from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
import re
from typing import Any
from urllib.parse import quote_plus

import httpx

from .multi_step_research import MultiStepResearchRuntime


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
    research_runtime: dict[str, Any] = field(default_factory=dict)


class DeepResearchEngine:
    """General public-web research, free-first and bounded by Bitey's runtime."""

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)
    RESULT_RE = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)

    def __init__(self, *, max_subquestions: int = 3, max_passes: int = 2, max_sources: int = 8) -> None:
        self.max_subquestions = max(1, max_subquestions)
        self.max_passes = max(1, max_passes)
        self.max_sources = max(1, max_sources)

    def plan(self, query: str, context: dict[str, Any] | None = None) -> DeepResearchPlan:
        context = context or {}
        q = query.lower()
        reasons: list[str] = []
        if self.URL_RE.search(query):
            reasons.append("explicit_url")
        if any(x in q for x in ("investiga", "busca", "fuentes", "compara", "contrasta", "research", "evidence")):
            reasons.append("research_intent")
        if any(x in q for x in ("último", "ultima", "última", "actual", "hoy", "latest", "current", "precio")):
            reasons.append("freshness")
        return DeepResearchPlan(query=query, reasons=reasons, mode=str(context.get("research_mode") or "deep"))

    async def _search(self, client: httpx.AsyncClient, query: str, limit: int = 5) -> list[str]:
        try:
            r = await client.get(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
            r.raise_for_status()
            urls: list[str] = []
            for href, _title in self.RESULT_RE.findall(r.text):
                href = unescape(href)
                if href.startswith("http") and href not in urls:
                    urls.append(href)
                if len(urls) >= limit:
                    break
            return urls
        except Exception:
            return []

    async def _research_query(self, query: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute exactly one bounded research unit for MultiStepResearchRuntime."""
        timeout = 15.0
        max_bytes = 500_000
        headers = {"User-Agent": "BiteyIA-DeepResearch/1.0"}
        evidence: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            urls = [u.rstrip(".,);]}") for u in self.URL_RE.findall(query)[:5]]
            urls = [u if u.lower().startswith(("http://", "https://")) else "https://" + u for u in urls]
            if not urls:
                urls = await self._search(client, query, limit=min(5, self.max_sources))
            for url in urls[: self.max_sources]:
                try:
                    r = await client.get(url)
                    r.raise_for_status()
                    ct = r.headers.get("content-type", "")
                    if "html" not in ct and "text/plain" not in ct:
                        evidence.append({"url": url, "ok": False, "error": "unsupported_content_type"})
                        continue
                    text = r.content[:max_bytes].decode(r.encoding or "utf-8", errors="replace")
                    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
                    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
                    text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
                    text = re.sub(r"<[^>]+>", " ", text)
                    text = unescape(re.sub(r"\s+", " ", text)).strip()
                    if len(text) < 80:
                        evidence.append({"url": str(r.url), "title": title, "ok": False, "error": "insufficient_text"})
                    else:
                        evidence.append({"url": str(r.url), "title": title, "content": text[:16000], "ok": True})
                except Exception as exc:
                    evidence.append({"url": url, "ok": False, "error": type(exc).__name__})
        usable = [item for item in evidence if item.get("ok") and item.get("content")]
        # Follow-up generation is deliberately deterministic. Bitey's Brain can
        # supply explicit subquestions; this layer never asks a model to invent
        # an unlimited research plan.
        follow_ups: list[str] = []
        if not usable and context.get("research_pass", 1) == 1:
            follow_ups.append(f"fuentes oficiales y evidencia sobre: {query}")
        return {
            "evidence": evidence,
            "sufficient": len(usable) >= 2,
            "minimum_evidence": 2,
            "follow_up_queries": follow_ups,
        }

    async def fetch(self, plan: DeepResearchPlan) -> DeepResearchPlan:
        if not plan.reasons:
            return plan

        runtime = MultiStepResearchRuntime(
            self._research_query,
            max_subquestions=self.max_subquestions,
            max_passes=self.max_passes,
            max_sources=self.max_sources,
        )
        result = await runtime.run(plan.query, {"research_mode": plan.mode})
        plan.research_runtime = result.as_dict()
        plan.evidence = [
            Evidence(
                url=str(item.get("url", "")),
                title=str(item.get("title", "")),
                content=str(item.get("content", "")),
                ok=bool(item.get("ok")),
                error=item.get("error"),
            )
            for item in result.evidence
            if item.get("url")
        ]
        plan.urls = [e.url for e in plan.evidence]
        return plan

    def evidence_context(self, plan: DeepResearchPlan) -> str:
        usable = [e for e in plan.evidence if e.ok and e.content]
        return "\n\n".join(f"SOURCE {i}: {e.url}\nTITLE: {e.title}\nEVIDENCE:\n{e.content}" for i, e in enumerate(usable, 1))

    def source_summary(self, plan: DeepResearchPlan) -> list[dict[str, Any]]:
        return [{"url": e.url, "title": e.title, "ok": e.ok, "error": e.error} for e in plan.evidence]
