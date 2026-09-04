from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import re
import httpx
from .web_research_policy import WebResearchPolicy

@dataclass
class ResearchPlan:
    required: bool
    query: str
    reasons: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    strategy: str = "none"
    confidence: float = 0.0

class ResearchEngine:
    """Evidence-first research decision boundary for independent Bitey IA."""
    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.IGNORECASE)

    def __init__(self, policy: WebResearchPolicy | None = None) -> None:
        self.policy = policy or WebResearchPolicy()

    def plan(self, message: str, context: dict[str, Any] | None = None) -> ResearchPlan:
        context = context if context is not None else {}
        decision = self.policy.decide(message, context)
        plan = ResearchPlan(required=decision.required, query=message, reasons=decision.reasons, strategy=decision.strategy, confidence=decision.confidence)
        # Explicit handoff: the deterministic research policy decision becomes
        # part of the cognitive context before Bitey Brain runs. Models never
        # decide whether research is required.
        context["research"] = {
            "required": decision.required,
            "confidence": decision.confidence,
            "reasons": list(decision.reasons),
            "strategy": decision.strategy,
            "owner": "bitey_research_policy",
        }
        return plan

    async def fetch_urls(self, message: str) -> list[dict[str, Any]]:
        raw_urls = self.URL_RE.findall(message)[:3]
        urls = [u.rstrip(".,);]}") for u in raw_urls]
        urls = [u if u.lower().startswith(("http://", "https://")) else f"https://{u}" for u in urls]
        if not urls: return []
        results=[]; headers={"User-Agent":"BiteyIA-Research/1.0"}; timeout=float(__import__("os").getenv("WEB_RESEARCH_TIMEOUT","15")); max_bytes=int(__import__("os").getenv("WEB_RESEARCH_MAX_BYTES","300000"))
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            for url in urls:
                try:
                    response=await client.get(url); response.raise_for_status(); content_type=response.headers.get("content-type","")
                    if "text/html" not in content_type and "text/plain" not in content_type:
                        results.append({"url":url,"ok":False,"error":"unsupported_content_type"}); continue
                    raw=response.content[:max_bytes]; text=raw.decode(response.encoding or "utf-8",errors="replace")
                    text=re.sub(r"<script[^>]*>.*?</script>"," ",text,flags=re.I|re.S); text=re.sub(r"<style[^>]*>.*?</style>"," ",text,flags=re.I|re.S); text=re.sub(r"<noscript[^>]*>.*?</noscript>"," ",text,flags=re.I|re.S); text=re.sub(r"<[^>]+>"," ",text); text=re.sub(r"\s+"," ",text).strip()
                    if len(text)<80: results.append({"url":str(response.url),"ok":False,"error":"insufficient_page_text"}); continue
                    results.append({"url":str(response.url),"ok":True,"content":text[:12000],"content_type":content_type})
                except Exception as exc: results.append({"url":url,"ok":False,"error":type(exc).__name__})
        return results
