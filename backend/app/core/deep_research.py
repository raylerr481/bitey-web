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
    research_passes: int = 0
    verification_required: bool = False
    query_variants: list[str] = field(default_factory=list)
    clarification_needed: bool = False


class DeepResearchEngine:
    """General public-web research, free-first and evidence-first."""

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)
    RESULT_RE = re.compile(r'<a[^>]+class=["\']result__a["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    BING_RESULT_RE = re.compile(r'<li[^>]+class=["\']b_algo["\'][^>]*>.*?<h2[^>]*>\s*<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    YEAR_RE = re.compile(r"\b20\d{2}\b")
    KNOWLEDGE_RE = re.compile(
        r"\b(?:qué es|que es|quién es|quien es|cómo funciona|como funciona|por qué|porque|"
        r"cuál es|cual es|dime|explícame|explicame|informa(?:me|r)?|quiero saber|"
        r"necesito saber|enséñame|ensename|muéstrame|muestrame|tell me|explain|"
        r"inform me|i want to know|i need to know|teach me)\b",
        re.I,
    )
    AMBIGUOUS_RE = re.compile(
        r"^(?:qué|que|quién|quien|cómo|como|cuál|cual|dime|explica(?:me)?|"
        r"inform(?:a|ame)?|ayuda(?:me)?|what|who|how|which|tell me|explain)\s*$",
        re.I,
    )
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

    def _build_query_variants(self, query: str, reasons: list[str]) -> list[str]:
        """Create search-ready reformulations when the user's wording is incomplete."""
        base = re.sub(r"\s+", " ", query).strip()
        variants: list[str] = [base]
        if self.AMBIGUOUS_RE.match(base) or len(base.split()) <= 2:
            variants.extend([f"{base} meaning", f"{base} explanation", f"{base} definition"])
        elif "knowledge_request" in reasons:
            variants.append(f"{base} explanation reliable sources")
        elif "freshness" in reasons:
            variants.append(f"{base} latest current information")
        elif "research_intent" in reasons:
            variants.append(f"{base} sources evidence")
        return list(dict.fromkeys(v for v in variants if v))[:4]

    def plan(self, query: str, context: dict[str, Any] | None = None) -> DeepResearchPlan:
        context = context or {}
        q = query.lower()
        reasons: list[str] = []
        if self.URL_RE.search(query):
            reasons.append("explicit_url")
        if any(x in q for x in ("investiga", "busca", "fuentes", "compara", "contrasta", "research", "evidence")):
            reasons.append("research_intent")
        if any(x in q for x in ("último", "ultima", "última", "actual", "ahora", "hoy", "latest", "current", "precio", "cotización", "cotizacion")):
            reasons.append("freshness")
        if self.KNOWLEDGE_RE.search(q):
            reasons.append("knowledge_request")
        if self.YEAR_RE.search(query):
            reasons.append("year_specific")
        if any(x in q for x in ("programado", "programada", "previsto", "prevista", "calendario", "schedule", "scheduled")):
            reasons.append("scheduled_fact")
        if self.MEDICAL_RE.search(q):
            reasons.append("medical_domain")
        if context.get("research_required"):
            reasons.append("required_research")
        reasons = list(dict.fromkeys(reasons))
        verification_required = bool(reasons and any(r in reasons for r in (
            "freshness", "knowledge_request", "research_intent", "medical_domain", "year_specific", "required_research"
        )))
        variants = self._build_query_variants(query, reasons)
        clarification_needed = bool(self.AMBIGUOUS_RE.match(query.strip()))
        return DeepResearchPlan(
            query=query,
            reasons=reasons,
            mode=str(context.get("research_mode") or "deep"),
            verification_required=verification_required,
            query_variants=variants,
            clarification_needed=clarification_needed,
        )

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

    @staticmethod
    def _source_key(url: str) -> str:
        """Normalize a source host so cross-checks can prefer independent publishers."""
        return re.sub(r"^www\.", "", (httpx.URL(url).host or "").lower()).strip()

    @classmethod
    def _is_medical_authority(cls, url: str) -> bool:
        host = cls._source_key(url)
        return any(host == domain or host.endswith("." + domain) for domain in cls.MEDICAL_AUTHORITY_DOMAINS)

    async def _search_wikipedia(self, client: httpx.AsyncClient, query: str, limit: int = 3) -> list[str]:
        """Fallback knowledge discovery when search-engine HTML is unavailable."""
        try:
            response = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": limit},
            )
            response.raise_for_status()
            data = response.json()
            urls = []
            for item in (data.get("query", {}).get("search") or []):
                title = str(item.get("title") or "").strip()
                if title:
                    urls.append("https://en.wikipedia.org/wiki/" + quote_plus(title.replace(" ", "_")))
            return urls
        except Exception:
            return []

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
                # Research each reformulation until enough distinct sources are collected.
                for variant in plan.query_variants or [plan.query]:
                    found = await self._search(client, variant, limit=4, medical="medical_domain" in plan.reasons)
                    if not found and "knowledge_request" in plan.reasons:
                        found = await self._search_wikipedia(client, variant, limit=3)
                    plan.research_passes += 1
                    for url in found:
                        if url not in urls:
                            urls.append(url)
                        if len(urls) >= 8:
                            break
                    if len(urls) >= 8:
                        break
            # Prefer independent publisher hosts for the evidence set. Keep
            # same-host pages only after distinct hosts have been exhausted.
            unique_urls = list(dict.fromkeys(urls))
            diverse_urls: list[str] = []
            seen_hosts: set[str] = set()
            for url in unique_urls:
                host = self._source_key(url)
                if host and host not in seen_hosts:
                    diverse_urls.append(url)
                    seen_hosts.add(host)
                if len(diverse_urls) >= 8:
                    break
            for url in unique_urls:
                if url not in diverse_urls:
                    diverse_urls.append(url)
                if len(diverse_urls) >= 8:
                    break
            plan.urls = diverse_urls[:8]
            if plan.urls and plan.research_passes == 0:
                plan.research_passes = 1
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

            # Discovery can succeed while every discovered page is blocked or
            # otherwise unusable. For knowledge questions, recover by querying
            # Wikipedia directly instead of treating discovery metadata as
            # verified evidence.
            if (
                "knowledge_request" in plan.reasons
                and not any(e.ok and e.content for e in plan.evidence)
            ):
                fallback_urls: list[str] = []
                for variant in plan.query_variants or [plan.query]:
                    for url in await self._search_wikipedia(client, variant, limit=3):
                        if url not in fallback_urls:
                            fallback_urls.append(url)
                        if len(fallback_urls) >= 3:
                            break
                    plan.research_passes += 1
                    if len(fallback_urls) >= 3:
                        break
                for url in fallback_urls:
                    if url in plan.urls:
                        continue
                    try:
                        r = await client.get(url)
                        r.raise_for_status()
                        ct = r.headers.get("content-type", "")
                        if "html" not in ct:
                            plan.evidence.append(Evidence(url=url, error="unsupported_content_type"))
                            continue
                        text = r.content[:max_bytes].decode(r.encoding or "utf-8", errors="replace")
                        title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
                        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
                        text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
                        text = re.sub(r"<[^>]+>", " ", text)
                        text = unescape(re.sub(r"\s+", " ", text)).strip()
                        if len(text) >= 80:
                            plan.evidence.append(Evidence(url=str(r.url), title=title, content=text[:16000], ok=True))
                        else:
                            plan.evidence.append(Evidence(url=str(r.url), title=title, error="insufficient_text"))
                    except Exception as exc:
                        plan.evidence.append(Evidence(url=url, error=type(exc).__name__))
        return plan

    def evidence_context(self, plan: DeepResearchPlan) -> str:
        usable = [e for e in plan.evidence if e.ok and e.content]
        if not usable:
            return ""
        source_header = (
            f"RESEARCH STATUS: {len(usable)} usable source(s); "
            f"verification_required={plan.verification_required}; passes={plan.research_passes}; "
            f"clarification_needed={plan.clarification_needed}; "
            f"query_variants={len(plan.query_variants)}"
        )
        query_info = "\n".join(f"RESEARCH QUERY {i}: {q}" for i, q in enumerate(plan.query_variants, 1))
        sources = "\n\n".join(
            f"SOURCE {i}: {e.url}\nTITLE: {e.title}\nEVIDENCE:\n{e.content}"
            for i, e in enumerate(usable, 1)
        )
        return f"{source_header}\n\n{query_info}\n\n{sources}"

    def source_summary(self, plan: DeepResearchPlan) -> list[dict[str, Any]]:
        return [
            {
                "url": e.url,
                "title": e.title,
                "ok": e.ok,
                "error": e.error,
                "verification_required": plan.verification_required,
                "query_variants": plan.query_variants,
                "clarification_needed": plan.clarification_needed,
            }
            for e in plan.evidence
        ]
