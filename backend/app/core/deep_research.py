from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
import re
from typing import Any
from urllib.parse import quote_plus

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
    mode: str = "multistep"
    reasons: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


class DeepResearchEngine:
    """General public-web research, free-first and evidence-first.

    The public fetch boundary routes through Bitey's bounded research runtime.
    ``fetch_single`` is the low-level evidence capability and never starts a
    second research pass, preventing recursive or unbounded orchestration.
    """

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)
    RESULT_RE = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)

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
        return DeepResearchPlan(query=query, reasons=reasons, mode=str(context.get("research_mode") or "multistep"))

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

    async def fetch_single(self, plan: DeepResearchPlan) -> DeepResearchPlan:
        """Fetch one question only; never orchestrate another pass."""
        timeout = 15.0
        max_bytes = 500_000
        headers = {"User-Agent": "BiteyIA-DeepResearch/1.0"}
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            urls = [u.rstrip(".,);]}") for u in self.URL_RE.findall(plan.query)[:5]]
            urls = [u if u.lower().startswith(("http://", "https://")) else "https://" + u for u in urls]
            if not urls and plan.reasons:
                urls = await self._search(client, plan.query, limit=5)
            plan.urls = list(dict.fromkeys(urls))[:5]
            for url in plan.urls:
                try:
                    r = await client.get(url)
                    r.raise_for_status()
                    ct = r.headers.get("content-type", "")
                    if "html" not in ct and "text/plain" not in ct:
                        plan.evidence.append(Evidence(url=url, error="unsupported_content_type"))
                        continue
                    text = r.content[:max_bytes].decode(r.encoding or "utf-8", errors="replace")
                    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
                    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
                    text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
                    text = re.sub(r"<[^>]+>", " ", text)
                    text = unescape(re.sub(r"\s+", " ", text)).strip()
                    if len(text) < 80:
                        plan.evidence.append(Evidence(url=str(r.url), title=title, error="insufficient_text"))
                    else:
                        plan.evidence.append(Evidence(url=str(r.url), title=title, content=text[:16000], ok=True))
                except Exception as exc:
                    plan.evidence.append(Evidence(url=url, error=type(exc).__name__))
        return plan

    async def fetch(self, plan: DeepResearchPlan) -> DeepResearchPlan:
        if plan.mode != "multistep":
            return await self.fetch_single(plan)
        from .multistep_research_runtime import MultiStepResearchRuntime
        runtime = MultiStepResearchRuntime(self)
        result = await runtime.run(plan.query, {"research_mode": "multistep"})
        plan.urls = list(dict.fromkeys(str(item.get("url")) for item in result.evidence if item.get("url")))[:20]
        plan.evidence = [
            Evidence(
                url=str(item.get("url") or ""),
                title=str(item.get("title") or ""),
                content=str(item.get("content") or ""),
                ok=bool(item.get("ok")),
                error=item.get("error"),
            )
            for item in result.evidence
        ]
        return plan

    def evidence_context(self, plan: DeepResearchPlan) -> str:
        usable = [e for e in plan.evidence if e.ok and e.content]
        return "\n\n".join(f"SOURCE {i}: {e.url}\nTITLE: {e.title}\nEVIDENCE:\n{e.content}" for i, e in enumerate(usable, 1))

    def source_summary(self, plan: DeepResearchPlan) -> list[dict[str, Any]]:
        return [{"url": e.url, "title": e.title, "ok": e.ok, "error": e.error} for e in plan.evidence]
