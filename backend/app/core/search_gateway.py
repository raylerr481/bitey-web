from __future__ import annotations

import html
import ipaddress
import re
import socket
from typing import Any
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen


BLOCKED_PROVIDERS = {"brave", "bing", "google"}


def _public_host(host: str) -> bool:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        return bool(addresses) and all(not ipaddress.ip_address(a).is_private and not ipaddress.ip_address(a).is_loopback and not ipaddress.ip_address(a).is_link_local and not ipaddress.ip_address(a).is_reserved and not ipaddress.ip_address(a).is_multicast for a in addresses)
    except Exception:
        return False


def _duckduckgo(query: str, limit: int) -> list[dict[str, Any]]:
    request = Request("https://html.duckduckgo.com/html/?q=" + quote(query), headers={"User-Agent": "BiteySearch/1.0"})
    with urlopen(request, timeout=8) as response:
        body = response.read().decode("utf-8", errors="ignore")
    blocks = re.findall(r'<div class="result__body".*?</div>\s*</div>', body, flags=re.S)
    results: list[dict[str, Any]] = []
    for block in blocks[: limit * 2]:
        match = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.S)
        if not match:
            continue
        raw_url = html.unescape(match.group(1))
        redirect = re.search(r"uddg=([^&]+)", raw_url)
        target = unquote(redirect.group(1)) if redirect else raw_url
        title = re.sub(r"<.*?>", "", html.unescape(match.group(2))).strip()
        snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>', block, flags=re.S)
        snippet = re.sub(r"<.*?>", "", html.unescape(snippet_match.group(1) if snippet_match else "")).strip()
        if target.startswith("http") and title:
            results.append({"url": target, "title": title, "snippet": snippet, "source": "duckduckgo"})
        if len(results) >= limit:
            break
    return results


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
        request = Request(url, headers={"Accept": "text/html,text/plain;q=0.9", "User-Agent": "BiteySearch/1.0"})
        with urlopen(request, timeout=8) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                return {"ok": False, "error": "unsupported_content_type"}
            raw = response.read(max_bytes)
        text = re.sub(r"(?is)<(script|style|noscript|svg|template).*?>.*?</\1>", " ", raw.decode("utf-8", errors="ignore"))
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        return {"ok": True, "url": url, "content": re.sub(r"\s+", " ", html.unescape(text)).strip()[:16000], "content_type": content_type}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}
