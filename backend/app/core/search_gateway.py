from __future__ import annotations

import html
import ipaddress
import re
import socket
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen


BLOCKED_PROVIDERS = {"brave", "bing", "google"}


def _public_host(host: str) -> bool:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        return bool(addresses) and all(
            not ipaddress.ip_address(a).is_private
            and not ipaddress.ip_address(a).is_loopback
            and not ipaddress.ip_address(a).is_link_local
            and not ipaddress.ip_address(a).is_reserved
            and not ipaddress.ip_address(a).is_multicast
            for a in addresses
        )
    except Exception:
        return False


def _clean_html(value: str) -> str:
    value = re.sub(r"(?is)<(script|style|noscript|svg|template).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _resolve_result_url(raw_url: str) -> str:
    raw_url = html.unescape(raw_url).strip()
    parsed = urlparse(raw_url)
    if parsed.netloc and parsed.netloc.lower().endswith("duckduckgo.com"):
        params = parse_qs(parsed.query)
        if params.get("uddg"):
            return unquote(params["uddg"][0])
    match = re.search(r"[?&]uddg=([^&]+)", raw_url)
    return unquote(match.group(1)) if match else raw_url


def _parse_duckduckgo(body: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    # The HTML endpoint has changed markup over time. Prefer result anchors and
    # locate their nearest result container rather than depending on one exact
    # nested <div> shape.
    anchor_pattern = re.compile(
        r'<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.I | re.S,
    )
    for match in anchor_pattern.finditer(body):
        target = _resolve_result_url(match.group(1))
        title = _clean_html(match.group(2))
        if not target.startswith(("http://", "https://")) or not title:
            continue
        key = target.rstrip("/").lower()
        if key in seen:
            continue
        # Search backwards to the current result container and forwards to the
        # next result. This remains tolerant of DDG markup changes.
        start = body.rfind("<div", 0, match.start())
        end = body.find('<a class="result__a"', match.end())
        container = body[start:end if end != -1 else min(len(body), match.end() + 5000)]
        snippet_match = re.search(
            r'class=["\'][^"\']*result__snippet[^"\']*["\'][^>]*>(.*?)</(?:a|div)>',
            container,
            re.I | re.S,
        )
        snippet = _clean_html(snippet_match.group(1)) if snippet_match else ""
        results.append({"url": target, "title": title, "snippet": snippet, "source": "duckduckgo"})
        seen.add(key)
        if len(results) >= limit:
            break
    return results


def _duckduckgo(query: str, limit: int) -> list[dict[str, Any]]:
    urls = [
        "https://html.duckduckgo.com/html/?q=" + quote(query),
        "https://lite.duckduckgo.com/lite/?q=" + quote(query),
    ]
    last_error: Exception | None = None
    for url in urls:
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; BiteySearch/1.0)",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urlopen(request, timeout=10) as response:
                body = response.read().decode("utf-8", errors="ignore")
            results = _parse_duckduckgo(body, limit)
            if results:
                return results
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    return []


def search(query: str, limit: int = 8) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return {"provider": "none", "results": [], "errors": []}
    try:
        results = _duckduckgo(query, max(1, min(limit, 20)))
        return {"provider": "duckduckgo", "results": results, "errors": []}
    except Exception as exc:
        return {"provider": "duckduckgo", "results": [], "errors": [type(exc).__name__]}


def safe_fetch(url: str, max_bytes: int = 120000) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or not _public_host(parsed.hostname):
        return {"ok": False, "error": "unsafe_url"}
    try:
        request = Request(
            url,
            headers={
                "Accept": "text/html,text/plain;q=0.9",
                "User-Agent": "Mozilla/5.0 (compatible; BiteySearch/1.0)",
            },
        )
        with urlopen(request, timeout=10) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                return {"ok": False, "error": "unsupported_content_type"}
            raw = response.read(max_bytes)
            final_url = str(response.url)
        text = _clean_html(raw.decode("utf-8", errors="ignore"))
        return {"ok": True, "url": final_url, "content": text[:16000], "content_type": content_type}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}
