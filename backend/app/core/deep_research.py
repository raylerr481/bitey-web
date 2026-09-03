from __future__ import annotations
from dataclasses import dataclass, field
from html import unescape
import os, re, time
from typing import Any
import httpx

@dataclass
class Evidence:
    url:str; title:str=""; content:str=""; ok:bool=False; error:str|None=None
@dataclass
class DeepResearchPlan:
    query:str; mode:str="adaptive"; reasons:list[str]=field(default_factory=list); queries:list[str]=field(default_factory=list); urls:list[str]=field(default_factory=list); evidence:list[Evidence]=field(default_factory=list); search_pages:int=0; search_exhausted:bool=False; contradiction_signal:bool=False
class DeepResearchEngine:
    """Language-driven adaptive research with pagination and evidence signals."""
    URL_RE=re.compile(r"(?:https?://|www\.)[^\s<>'\"]+",re.I); RESULT_RE=re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',re.I|re.S)
    def plan(self,query:str,context:dict[str,Any]|None=None)->DeepResearchPlan:
        context=context or {}; reasons=[]
        if self.URL_RE.search(query): reasons.append("explicit_url")
        if context.get("external_information_required") or context.get("evidence_required"): reasons.append("orchestrator_request")
        if context.get("research") or context.get("research_requested"): reasons.append("research_request")
        return DeepResearchPlan(query=query,reasons=reasons,mode=str(context.get("research_mode") or "adaptive"),queries=[query])
    @staticmethod
    def _query_variants(query:str)->list[str]: return list(dict.fromkeys([query.strip(),f"{query.strip()} fuentes oficiales",f"{query.strip()} evidencia",f"{query.strip()} datos actuales"]))
    async def _search(self,client:httpx.AsyncClient,query:str,*,deadline:float)->tuple[list[str],bool,int]:
        urls=[]; page=0
        while time.monotonic()<deadline:
            try:
                r=await client.get("https://html.duckduckgo.com/html/",params={"q":query,"s":page*30}); r.raise_for_status(); matches=self.RESULT_RE.findall(r.text); found=0
                for href,_ in matches:
                    href=unescape(href)
                    if href.startswith("http") and href not in urls: urls.append(href); found+=1
                page+=1
                if not matches or not found: return urls,True,page
            except Exception: return urls,False,page
        return urls,False,page
    async def fetch(self,plan:DeepResearchPlan)->DeepResearchPlan:
        timeout=float(os.getenv("WEB_RESEARCH_TIMEOUT","15")); max_bytes=int(os.getenv("WEB_RESEARCH_MAX_BYTES","500000")); budget=max(5.0,float(os.getenv("WEB_RESEARCH_BUDGET_SECONDS","45"))); deadline=time.monotonic()+budget
        async with httpx.AsyncClient(timeout=timeout,follow_redirects=True,headers={"User-Agent":"BiteyIA-DeepResearch/3.0"}) as client:
            urls=[u.rstrip(".,);]}") for u in self.URL_RE.findall(plan.query)]; urls=[u if u.lower().startswith(("http://","https://")) else "https://"+u for u in urls]
            if not urls and plan.reasons:
                for query in self._query_variants(plan.query):
                    if query not in plan.queries: plan.queries.append(query)
                    found,exhausted,pages=await self._search(client,query,deadline=deadline); urls.extend(found); plan.search_pages+=pages; plan.search_exhausted=plan.search_exhausted or exhausted
                    if time.monotonic()>=deadline: break
            plan.urls=list(dict.fromkeys(urls))
            for url in plan.urls:
                if time.monotonic()>=deadline: break
                try:
                    r=await client.get(url); r.raise_for_status(); ct=r.headers.get("content-type","")
                    if "html" not in ct and "text/plain" not in ct: plan.evidence.append(Evidence(url=url,error="unsupported_content_type")); continue
                    text=r.content[:max_bytes].decode(r.encoding or "utf-8",errors="replace"); tm=re.search(r"<title[^>]*>(.*?)</title>",text,re.I|re.S); title=re.sub(r"\s+"," ",tm.group(1)).strip() if tm else ""; text=re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>"," ",text,flags=re.I|re.S); text=re.sub(r"<[^>]+>"," ",text); text=unescape(re.sub(r"\s+"," ",text)).strip()
                    plan.evidence.append(Evidence(url=str(r.url),title=title,content=text[:16000],ok=len(text)>=80) if len(text)>=80 else Evidence(url=str(r.url),title=title,error="insufficient_text"))
                except Exception as exc: plan.evidence.append(Evidence(url=url,error=type(exc).__name__))
        plan.contradiction_signal=self._numeric_conflict(plan.evidence); return plan
    @staticmethod
    def _numeric_conflict(evidence:list[Evidence])->bool:
        claims={}
        for e in evidence:
            if not e.ok: continue
            for sentence in re.split(r"(?<=[.!?])\s+",e.content):
                nums=re.findall(r"[-+]?\d+(?:[.,]\d+)?",sentence)
                if nums:
                    key=re.sub(r"[-+]?\d+(?:[.,]\d+)?","#",sentence.lower()); claims.setdefault(key,set()).update(nums)
        return any(len(v)>1 for v in claims.values())
    def evidence_context(self,plan:DeepResearchPlan)->str:
        return "\n\n".join(f"SOURCE {i}: {e.url}\nTITLE: {e.title}\nEVIDENCE:\n{e.content}" for i,e in enumerate([x for x in plan.evidence if x.ok and x.content],1))
    def source_summary(self,plan:DeepResearchPlan)->list[dict[str,Any]]: return [{"url":e.url,"title":e.title,"ok":e.ok,"error":e.error} for e in plan.evidence]
