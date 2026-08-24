from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

import httpx


@dataclass
class Evidence:
    url: str
    title: str = ""
    content: str = ""
    ok: bool = False
    error: str | None = None


@dataclass
class DeepResearchPlan:
    query: str
    mode: str = "deep"
    reasons: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


class DeepResearchEngine:
    """Public-web, evidence-first research layer. It never treats failed retrieval as evidence."""

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)

    def plan(self, query: str, context: dict[str, Any] | None = None) -> DeepResearchPlan:
        context = context or {}
        q = query.lower()
        reasons: list[str] = []
        if self.URL_RE.search(query):
            reasons.append("explicit_url")
        if any(x in q for x in ("investiga", "compara", "contrasta", "fuentes", "research", "evidence")):
            reasons.append("research_intent")
        if any(x in q for x in ("último", "ultima", "última", "actual", "hoy", "latest", "current", "precio")):
            reasons.append("freshness")
        return DeepResearchPlan(query=query, reasons=reasons, mode=str(context.get("research_mode") or "deep"))

    async def fetch(self, plan: DeepResearchPlan) -> DeepResearchPlan:
        urls = [u.rstrip(".,);]}") for u in self.URL_RE.findall(plan.query)[:5]]
        urls = [u if u.lower().startswith(("http://", "https://")) else "https://" + u for u in urls]
        plan.urls = urls
        if not urls:
            return plan

        timeout = 15.0
        max_bytes = 500_000
        headers = {"User-Agent": "BiteyIA-DeepResearch/1.0"}
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            for url in urls:
                try:
                    r = await client.get(url)
                    r.raise_for_status()
                    ct = r.headers.get("content-type", "")
                    if "html" not in ct and "text/plain" not in ct:
                        plan.evidence.append(Evidence(url=url, error="unsupported_content_type"))
                        continue
                    text = r.content[:max_bytes].decode(r.encoding or "utf-8", errors="replace")
                    title = ""
                    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
                    if title_match:
                        title = re.sub(r"\s+", " ", title_match.group(1)).strip()
                    text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
                    text = re.sub(r"<[^>]+>", " ", text)
                    text = re.sub(r"\s+", " ", text).strip()
                    if len(text) < 80:
                        plan.evidence.append(Evidence(url=str(r.url), title=title, error="insufficient_text"))
                    else:
                        plan.evidence.append(Evidence(url=str(r.url), title=title, content=text[:16000], ok=True))
                except Exception as exc:
                    plan.evidence.append(Evidence(url=url, error=type(exc).__name__))
        return plan

    def evidence_context(self, plan: DeepResearchPlan) -> str:
        usable = [e for e in plan.evidence if e.ok and e.content]
        if not usable:
            return ""
        return "\n\n".join(
            f"SOURCE {i}: {e.url}\nTITLE: {e.title}\nEVIDENCE:\n{e.content}"
            for i, e in enumerate(usable, 1)
        )

    def source_summary(self, plan: DeepResearchPlan) -> list[dict[str, Any]]:
        return [{"url": e.url, "title": e.title, "ok": e.ok, "error": e.error} for e in plan.evidence]
