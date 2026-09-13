from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
import re
from typing import Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

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
    """General public-web research, free-first and evidence-first."""

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)
    RESULT_RE = re.compile(r'<a[^>]+class=["\']result__a["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    BING_RESULT_RE = re.compile(r'<li[^>]+class=["\']b_algo["\'][^>]*>.*?<h2[^>]*>\s*<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    YEAR_RE = re.compile(r"\b20\d{2}\b")
    MEDICAL_RE = re.compile(
        r"\b(?:salud|health|enfermedad|enfermedades|síntoma|síntomas|sintoma|sintomas|"
        r"sida|vih|hiv|tratamiento|tratamientos|medicina|médico|médica|medical|"
        r"diagnóstico|diagnostico|infection|infección|infecciones|cáncer|cancer|"
        r"virus|bacteria|vacuna|vacunación|hospital|medicación|medicamento|"
        r"disease|symptom|treatment|diagnosis)\b",
        re.I,
    )
    MEDICAL_AUTHORITY_QUERIES = (
        "site:who.int OR site:paho.org",
        "site:cdc.gov OR site:nih.gov",
        "site:gov.br/saude OR site:fiocruz.br",
    )
    MEDICAL_AUTHORITY_DOMAINS = (
        "who.int", "paho.org", "cdc.gov", "nih.gov", "gov.br", "fiocruz.br", "unaids.org"
    )

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
        if self.YEAR_RE.search(query):
            reasons.append("year_specific")
        if any(x in q for x in ("programado", "programada", "previsto", "prevista", "calendario", "schedule", "scheduled")):
            reasons.append("scheduled_fact")
        if self.MEDICAL_RE.search(q):
            reasons.append("medical_domain")
        if context.get("research_required"):
            reasons.append("required_research")
        return DeepResearchPlan(query=query, reasons=list(dict.fromkeys(reasons)), mode=str(context.get("research_mode") or "deep"))

    @staticmethod
    def _clean_result_url(href: str) -> str:
        href = unescape(href).strip()
        if href.startswith("//"):
            href = "https:" + href
        return href

    async def _search_duckduckgo(self, client: httpx.AsyncClient, query: str, limit: int = 5) -> list[str]:
        try:
            r = await client.get(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
            r.raise_for_status()
            urls: list[str] = []
            for href, _title in self.RESULT_RE.findall(r.text):
                href = self._clean_result_url(href)
                if href.startswith("http") and "duckduckgo.com" not in href and href not in urls:
                    urls.append(href)
                if len(urls) >= limit:
                    break
            return urls
        except Exception:
            return []

    async def _search_bing(self, client: httpx.AsyncClient, query: str, limit: int = 5) -> list[str]:
        try:
            r = await client.get(f"https://www.bing.com/search?q={quote_plus(query)}")
            r.raise_for_status()
            urls: list[str] = []
            for href, _title in self.BING_RESULT_RE.findall(r.text):
                href = self._clean_result_url(href)
                if href.startswith("http") and "bing.com" not in href and href not in urls:
                    urls.append(href)
                if len(urls) >= limit:
                    break
            return urls
        except Exception:
            return []

    async def _search_bing_rss(self, client: httpx.AsyncClient, query: str, limit: int = 5) -> list[str]:
        """Fallback to Bing RSS when HTML result markup changes or is blocked."""
        try:
            r = await client.get(f"https://www.bing.com/search?format=rss&q={quote_plus(query)}")
            r.raise_for_status()
            root = ET.fromstring(r.text)
            urls: list[str] = []
            for item in root.findall(".//item"):
                link = item.findtext("link")
                if not link:
                    continue
                href = self._clean_result_url(link)
                if href.startswith("http") and "bing.com" not in href and href not in urls:
                    urls.append(href)
                if len(urls) >= limit:
                    break
            return urls
        except Exception:
            return []

    @classmethod
    def _is_medical_authority(cls, url: str) -> bool:
        host = re.sub(r"^www\.", "", (httpx.URL(url).host or "").lower())
        return any(host == domain or host.endswith("." + domain) for domain in cls.MEDICAL_AUTHORITY_DOMAINS)

    async def _search(self, client: httpx.AsyncClient, query: str, limit: int = 5, medical: bool = False) -> list[str]:
        urls: list[str] = []
        if medical:
            for hint in self.MEDICAL_AUTHORITY_QUERIES:
                targeted = await self._search_duckduckgo(client, f"{query} {hint}", limit=2)
                if not targeted:
                    targeted = await self._search_bing(client, f"{query} {hint}", limit=2)
                for url in targeted:
                    if url not in urls:
                        urls.append(url)
                    if len(urls) >= limit:
                        return urls[:limit]
        generic = await self._search_duckduckgo(client, query, limit=limit)
        if len(generic) < limit:
            for url in await self._search_bing(client, query, limit=limit):
                if url not in generic:
                    generic.append(url)
                if len(generic) >= limit:
                    break
        if len(generic) < limit:
            for url in await self._search_bing_rss(client, query, limit=limit):
                if url not in generic:
                    generic.append(url)
                if len(generic) >= limit:
                    break
        for url in generic:
            if url not in urls:
                urls.append(url)
        if medical:
            urls.sort(key=lambda url: (not self._is_medical_authority(url), urls.index(url)))
        return urls[:limit]

    async def fetch(self, plan: DeepResearchPlan) -> DeepResearchPlan:
        timeout = 15.0
        max_bytes = 500_000
        headers = {"User-Agent": "BiteyIA-DeepResearch/1.0"}
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            urls = [u.rstrip(".,);]}") for u in self.URL_RE.findall(plan.query)[:5]]
            urls = [u if u.lower().startswith(("http://", "https://")) else "https://" + u for u in urls]
            if not urls and plan.reasons:
                urls = await self._search(client, plan.query, limit=5, medical="medical_domain" in plan.reasons)
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

    def evidence_context(self, plan: DeepResearchPlan) -> str:
        usable = [e for e in plan.evidence if e.ok and e.content]
        return "\n\n".join(f"SOURCE {i}: {e.url}\nTITLE: {e.title}\nEVIDENCE:\n{e.content}" for i, e in enumerate(usable, 1))

    def source_summary(self, plan: DeepResearchPlan) -> list[dict[str, Any]]:
        return [{"url": e.url, "title": e.title, "ok": e.ok, "error": e.error} for e in plan.evidence]
