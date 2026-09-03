from dataclasses import dataclass, field
from typing import Any
import re

import httpx


@dataclass
class ResearchPlan:
    required: bool
    query: str
    reasons: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)


class ResearchEngine:
    """Evidence-first web research adapter for independent Bitey IA."""

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.IGNORECASE)

    def plan(self, message: str, context: dict[str, Any]) -> ResearchPlan:
        explicit = bool(context.get("research", {}).get("requested"))
        has_url = bool(self.URL_RE.search(message))
        freshness_terms = ("latest", "today", "current", "actual", "precio", "price", "2026", "último", "ultima", "última", "hoy")
        needs_freshness = any(term in message.lower() for term in freshness_terms)
        required = explicit or has_url or needs_freshness
        reasons = []
        if explicit: reasons.append("research_requested")
        if has_url: reasons.append("url_requested")
        if needs_freshness: reasons.append("freshness_sensitive")
        return ResearchPlan(required=required, query=message, reasons=reasons)

    async def fetch_urls(self, message: str) -> list[dict[str, Any]]:
        raw_urls = self.URL_RE.findall(message)[:3]
        urls = [u.rstrip(".,);]}") for u in raw_urls]
        urls = [u if u.lower().startswith(("http://", "https://")) else f"https://{u}" for u in urls]
        if not urls: return []
        results: list[dict[str, Any]] = []
        headers = {"User-Agent": "BiteyIA-Research/1.0"}
        timeout = float(__import__("os").getenv("WEB_RESEARCH_TIMEOUT", "15"))
        max_bytes = int(__import__("os").getenv("WEB_RESEARCH_MAX_BYTES", "300000"))
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            for url in urls:
                try:
                    response = await client.get(url); response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type and "text/plain" not in content_type:
                        results.append({"url": url, "ok": False, "error": "unsupported_content_type"}); continue
                    raw = response.content[:max_bytes]
                    text = raw.decode(response.encoding or "utf-8", errors="replace")
                    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
                    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
                    text = re.sub(r"<noscript[^>]*>.*?</noscript>", " ", text, flags=re.I | re.S)
                    text = re.sub(r"<[^>]+>", " ", text); text = re.sub(r"\s+", " ", text).strip()
                    if len(text) < 80:
                        results.append({"url": str(response.url), "ok": False, "error": "insufficient_page_text"}); continue
                    results.append({"url": str(response.url), "ok": True, "content": text[:12000], "content_type": content_type})
                except Exception as exc:
                    results.append({"url": url, "ok": False, "error": type(exc).__name__})
        return results
