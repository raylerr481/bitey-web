from __future__ import annotations

import html
import ipaddress
import re
import socket
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen


BLOCKED_PROVIDERS = {"brave", "bing", "google"}
SEARCH_TIMEOUT_SECONDS = 8


def _public_host(host: str) -> bool:
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        }
        return bool(addresses) and all(
            not ipaddress.ip_address(address).is_private
            and not ipaddress.ip_address(address).is_loopback
            and not ipaddress.ip_address(address).is_link_local
            and not ipaddress.ip_address(address).is_reserved
            and not ipaddress.ip_address(address).is_multicast
            for address in addresses
        )
    except Exception:
        return False


def _clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _resolve_result_url(raw_url: str) -> str:
    raw_url = html.unescape(raw_url or "")
    parsed = urlparse(raw_url)
    if parsed.query:
        params = parse_qs(parsed.query)
        redirected = params.get("uddg", [None])[0]
        if redirected:
            return unquote(redirected)
    return raw_url


def _duckduckgo_html(query: str, limit: int) -> list[dict[str, Any]]:
    request = Request(
        "https://html.duckduckgo.com/html/?q=" + quote(query),
        headers={"User-Agent": "BiteySearch/2.0"},
    )
    with urlopen(request, timeout=SEARCH_TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8", errors="ignore")

    # DDG changes markup periodically. Prefer semantic result containers and
    # fall back to result links instead of requiring one exact nested structure.
    blocks = re.findall(
        r'<(?:div|article)[^>]+class=["'][^"']*result[^"']*["'][^>]*>.*?</(?:div|article)>',
        body,
        flags=re.I | re.S,
    )
    if not blocks:
        blocks = re.findall(
            r'<a[^>]+class=["'][^"']*result__a[^"']*["'][^>]*>.*?</a>',
            body,
            flags=re.I | re.S,
        )

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for block in blocks:
        match = re.search(
            r'class=["'][^"']*result__a[^"']*["'][^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>',
            block,
            flags=re.I | re.S,
        )
        if not match:
            # Some DDG variants put href before class.
            match = re.search(
                r'<a[^>]+href=["']([^"']+)["'][^>]+class=["'][^"']*result__a[^"']*["'][^>]*>(.*?)</a>',
                block,
                flags=re.I | re.S,
            )
        if not match:
            continue

        target = _resolve_result_url(match.group(1))
        title = _clean_text(match.group(2))
        if not target.startswith(("http://", "https://")) or not title:
            continue
        if target in seen:
            continue

        snippet_match = re.search(
            r'class=["'][^"']*result__snippet[^"']*["'][^>]*>(.*?)</(?:a|div|span)>',
            block,
            flags=re.I | re.S,
        )
        snippet = _clean_text(snippet_match.group(1) if snippet_match else "")
        results.append(
            {
                "url": target,
                "title": title,
                "snippet": snippet,
                "source": "duckduckgo",
            }
        )
        seen.add(target)
        if len(results) >= limit:
            break
    return results


def _duckduckgo_lite(query: str, limit: int) -> list[dict[str, Any]]:
    request = Request(
        "https://lite.duckduckgo.com/lite/?q=" + quote(query),
        headers={"User-Agent": "BiteySearch/2.0"},
    )
    with urlopen(request, timeout=SEARCH_TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8", errors="ignore")

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for href, label in re.findall(
        r'<a[^>]+href=["']([^"']+)["'][^>]*>(.*?)</a>',
        body,
        flags=re.I | re.S,
    ):
        target = _resolve_result_url(href)
        title = _clean_text(label)
        if (
            not target.startswith(("http://", "https://"))
            or not title
            or target in seen
            or "duckduckgo.com" in urlparse(target).netloc
        ):
            continue
        results.append(
            {
                "url": target,
                "title": title,
                "snippet": "",
                "source": "duckduckgo-lite",
            }
        )
        seen.add(target)
        if len(results) >= limit:
            break
    return results


def _dedupe_results(results: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        url = str(result.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        output.append(result)
        if len(output) >= limit:
            break
    return output


def search(query: str, limit: int = 8) -> dict[str, Any]:
    query = (query or "").strip()
    limit = max(1, min(int(limit), 20))
    if not query:
        return {"provider": "none", "results": [], "errors": []}

    errors: list[str] = []
    results: list[dict[str, Any]] = []

    try:
        results = _duckduckgo_html(query, limit)
    except Exception as exc:
        errors.append(f"duckduckgo:{type(exc).__name__}")

    # A second free endpoint prevents a parser/markup change in the primary
    # endpoint from turning every research request into an empty result set.
    if len(results) < limit:
        try:
            results = _dedupe_results(
                results + _duckduckgo_lite(query, limit),
                limit,
            )
        except Exception as exc:
            errors.append(f"duckduckgo-lite:{type(exc).__name__}")

    provider = "duckduckgo" if results else "none"
    return {
        "provider": provider,
        "results": results,
        "errors": errors,
        "result_count": len(results),
        "research_available": bool(results),
    }


def safe_fetch(url: str, max_bytes: int = 120000) -> dict[str, Any]:
    parsed = urlparse(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or not _public_host(parsed.hostname)
    ):
        return {"ok": False, "error": "unsafe_url"}
    try:
        request = Request(
            url,
            headers={
                "Accept": "text/html,text/plain;q=0.9",
                "User-Agent": "BiteySearch/2.0",
            },
        )
        with urlopen(request, timeout=SEARCH_TIMEOUT_SECONDS) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                return {"ok": False, "error": "unsupported_content_type"}
            raw = response.read(max_bytes)
        text = re.sub(
            r"(?is)<(script|style|noscript|svg|template).*?>.*?</\1>",
            " ",
            raw.decode("utf-8", errors="ignore"),
        )
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        return {
            "ok": True,
            "url": url,
            "content": re.sub(r"\s+", " ", html.unescape(text)).strip()[:16000],
            "content_type": content_type,
        }
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}
