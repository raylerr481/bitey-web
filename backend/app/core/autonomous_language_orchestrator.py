from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from typing import Any

@dataclass(frozen=True)
class LanguagePlan:
    intent:str; domain:str; capabilities:tuple[str,...]; external_information_required:bool; freshness_required:bool; verification_required:bool; search_objective:str; confidence:float; reasons:tuple[str,...]
    def as_dict(self)->dict[str,Any]: return asdict(self)

class AutonomousLanguageOrchestrator:
    """Language-first executive planner; registry remains the capability authority."""
    URL_RE=re.compile(r"(?:https?://|www\.)[^\s<>'\"]+",re.I)
    FRESHNESS=("hoy","ahora","actual","actualmente","reciente","último","última","latest","current","today","now","precio","cotización","noticia","noticias","qué pasó","que paso","cuánto cuesta","cuanto cuesta")
    RESEARCH=("investiga","investigar","busca","buscar","comprueba","verifica","contrasta","fuentes","evidencia","research","compare","compara")
    WEATHER=("tiempo","clima","temperatura","lluvia","humedad","viento","weather","forecast")
    FILES=("archivo","documento","pdf","fichero","imagen","file","document")
    CODE=("código","codigo","python","javascript","programa","debug","github","api","error")
    MATH=("calcula","cálculo","calculo","porcentaje","math")
    def plan(self,message:str,context:dict[str,Any]|None=None)->LanguagePlan:
        ctx=context or {}; q=f" {message.lower().strip()} "; reasons=[]; capabilities=[]
        freshness=any(x in q for x in self.FRESHNESS); research=bool(ctx.get("research")) or bool(ctx.get("evidence_required")) or any(x in q for x in self.RESEARCH); external=bool(ctx.get("external_information_required")) or freshness or research or bool(self.URL_RE.search(message))
        if any(x in q for x in self.WEATHER): capabilities.append("weather"); reasons.append("live_weather_intent")
        if self.URL_RE.search(message): reasons.append("explicit_external_resource")
        if research: capabilities.append("web_research"); reasons.append("external_evidence_intent")
        if any(x in q for x in self.FILES): capabilities.append("workspace_files"); reasons.append("workspace_context")
        if any(x in q for x in self.CODE): capabilities.append("code_reasoning"); reasons.append("technical_reasoning")
        if any(x in q for x in self.MATH) or re.search(r"\d+\s*[+\-*/%^]\s*\d+",q): capabilities.append("calculator"); reasons.append("numeric_computation")
        if external and not capabilities: capabilities.append("web_research"); reasons.append("language_context_requires_external_information")
        if external and freshness and "web_research" not in capabilities: capabilities.append("web_research"); reasons.append("freshness_requires_external_evidence")
        intent="answer_or_assist" if not capabilities and not external else "retrieve_then_reason" if any(x in capabilities for x in ("web_research","weather")) else "use_capability_then_reason"
        domain=str(ctx.get("domain") or "general")
        if "weather" in capabilities: domain="weather"
        elif "code_reasoning" in capabilities: domain="programming"
        elif "web_research" in capabilities and domain=="general": domain="research"
        elif "calculator" in capabilities: domain="math"
        verification=research or freshness or "web_research" in capabilities; objective="answer the user's goal" if not external else f"obtain trustworthy external evidence to answer: {message.strip()}"; confidence=min(0.98,0.60+0.08*len(reasons)+(0.10 if external else 0.0))
        return LanguagePlan(intent,domain,tuple(dict.fromkeys(capabilities)),external,freshness,verification,objective,confidence,tuple(dict.fromkeys(reasons)))
    def status(self)->dict[str,Any]: return {"name":"Autonomous Language Orchestrator","version":"1.1.0","mode":"language_first_adaptive","model_is_advisor":True,"runtime_registry_is_authority":True,"adaptive_search":True}
