from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from typing import Any

from .native_model.adapter import NativeLanguageModelAdapter

@dataclass(frozen=True)
class LanguagePlan:
    intent: str
    domain: str
    capabilities: tuple[str, ...]
    external_information_required: bool
    freshness_required: bool
    verification_required: bool
    search_objective: str
    confidence: float
    reasons: tuple[str, ...]
    query_strategy: tuple[str, ...] = ()
    source: str = "deterministic"
    def as_dict(self) -> dict[str, Any]: return asdict(self)

class AutonomousLanguageOrchestrator:
    """Language-first planner with optional local structured intelligence and deterministic fallback."""
    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)
    FRESHNESS = ("hoy","ahora","actual","actualmente","reciente","último","última","latest","current","today","now","precio","precios","cotización","cotizacion","noticia","noticias","qué pasó","que paso","hoje","agora","atual","recente","preço","notícia")
    RESEARCH = ("investiga","investigar","busca","buscar","comprueba","verifica","contrasta","fuentes","evidencia","pruebas","research","compare","compara","pesquisa","fontes","evidências","verifique")
    WEATHER = ("tiempo","clima","temperatura","lluvia","humedad","viento","weather","forecast","tempo","chuva","umidade","vento","previsão")
    FILES = ("archivo","archivos","documento","documentos","pdf","fichero","imagen","file","document","arquivo")
    CODE = ("código","codigo","python","javascript","programa","debug","github","api","error","code","programação")
    MATH = ("calcula","cálculo","calculo","porcentaje","math","calculate","calcule","percentual")
    EXTERNAL = ("web","internet","online","externa","externo","público","publica","public","site","sitio")

    def __init__(self) -> None:
        self.native_model = NativeLanguageModelAdapter()

    def _deterministic_plan(self, message: str, context: dict[str, Any] | None = None) -> LanguagePlan:
        ctx=context or {}; q=f" {message.lower().strip()} "; reasons=[]; capabilities=[]
        freshness=any(x in q for x in self.FRESHNESS)
        research=bool(ctx.get("research")) or bool(ctx.get("research_requested")) or bool(ctx.get("evidence_required")) or any(x in q for x in self.RESEARCH)
        explicit_url=bool(self.URL_RE.search(message))
        external=bool(ctx.get("external_information_required")) or freshness or research or explicit_url or any(x in q for x in self.EXTERNAL)
        if any(x in q for x in self.WEATHER): capabilities.append("weather"); reasons.append("live_weather_intent")
        if explicit_url: reasons.append("explicit_external_resource")
        if research or (external and not any(x in q for x in self.FILES+self.CODE+self.MATH+self.WEATHER)):
            capabilities.append("web_research"); reasons.append("external_evidence_intent")
        if any(x in q for x in self.FILES): capabilities.append("workspace_files"); reasons.append("workspace_context")
        if any(x in q for x in self.CODE): capabilities.append("code_reasoning"); reasons.append("technical_reasoning")
        if any(x in q for x in self.MATH) or re.search(r"\d+\s*[+\-*/%^]\s*\d+",q): capabilities.append("calculator"); reasons.append("numeric_computation")
        if freshness and "web_research" not in capabilities and "weather" not in capabilities: capabilities.append("web_research"); reasons.append("freshness_requires_external_evidence")
        capabilities=list(dict.fromkeys(capabilities))
        intent="answer_or_assist" if not capabilities and not external else "retrieve_then_reason" if any(x in capabilities for x in ("web_research","weather")) else "use_capability_then_reason"
        domain=str(ctx.get("domain") or "general")
        if "weather" in capabilities: domain="weather"
        elif "code_reasoning" in capabilities: domain="programming"
        elif "web_research" in capabilities and domain=="general": domain="research"
        elif "calculator" in capabilities and domain=="general": domain="math"
        verification=research or freshness or "web_research" in capabilities
        objective="answer the user's goal" if not external else f"obtain trustworthy external evidence to answer: {message.strip()}"
        strategy=("broad_discovery","source_diversification","evidence_scoring","contradiction_check","refine_until_sufficient") if "web_research" in capabilities else ()
        confidence=min(0.99,0.62+0.06*len(reasons)+(0.10 if external else 0.0))
        return LanguagePlan(intent,domain,tuple(capabilities),external,freshness,verification,objective,confidence,tuple(dict.fromkeys(reasons)),strategy,"deterministic")

    async def plan_async(self, message: str, context: dict[str, Any] | None = None) -> LanguagePlan:
        ctx=context or {}
        native = await self.native_model.plan(message, ctx)
        if native is not None:
            # The model proposes language intent; runtime validation owns capabilities.
            allowed = set((ctx.get("available_capabilities") or native.capabilities))
            capabilities = tuple(c for c in native.capabilities if c in allowed)
            return LanguagePlan(native.intent,native.domain,capabilities,native.external_information_required,native.freshness_required,native.verification_required,native.search_objective,native.confidence,native.reasons,native.query_strategy,"ollama")
        return self._deterministic_plan(message, ctx)

    def plan(self, message: str, context: dict[str, Any] | None = None) -> LanguagePlan:
        # Synchronous compatibility path; async runtime should call plan_async for Ollama.
        return self._deterministic_plan(message, context)

    async def status_async(self) -> dict[str, Any]:
        native = await self.native_model.health()
        return {**self.status(), "native_model": native, "semantic_planning": native.get("available", False)}

    def status(self)->dict[str,Any]:
        return {"name":"Autonomous Language Orchestrator","version":"3.0.0","mode":"language_first_adaptive","semantic_planning":False,"model_is_advisor":True,"runtime_registry_is_authority":True,"adaptive_search":True,"no_fixed_result_cap":True,"multilingual":True,"deterministic_fallback":True}
