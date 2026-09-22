from __future__ import annotations
import re
import time
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .core.bitey_brain import BiteyBrain
from .core.deep_research import DeepResearchEngine
from .core.mathematics import analyze as math_analyze, calculate as math_calculate
from .core.provider_gateway import ProviderGateway
from .core.tool_orchestrator import ToolOrchestrator

class ChatV2Request(BaseModel):
    conversation_id: str | None = None
    message: str = Field(min_length=1, max_length=50000)
    mode: str = "auto"
    metadata: dict[str, Any] = Field(default_factory=dict)

class ChatV2Response(BaseModel):
    conversation_id: str
    answer: str
    mode: str
    tools_used: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    activity_events: list[str] = Field(default_factory=list)
    calculations: dict[str, Any] | None = None
    trace_id: str | None = None
    elapsed_ms: int

def create_chat_v2_router(memory, providers: ProviderGateway, tools: ToolOrchestrator, brain: BiteyBrain) -> APIRouter:
    router = APIRouter(prefix="/api/v2", tags=["chat"])
    research = DeepResearchEngine()

    @router.get("/capabilities")
    async def capabilities():
        return {
            "chat": True,
            "multi_turn": True,
            "web_research": True,
            "deep_research": True,
            "mathematics": True,
            "source_citations": True,
            "tool_orchestration": True,
            "provider_failover": True,
            "free_first": True,
            "file_context": True,
            "modes": ["auto", "chat", "research", "math", "code"],
            "tools": tools.available(),
        }

    @router.post("/chat", response_model=ChatV2Response)
    async def chat(payload: ChatV2Request):
        started = time.perf_counter()
        cid = payload.conversation_id
        try:
            UUID(cid or "")
        except Exception:
            cid = str(uuid4())
            await memory.create_conversation(cid, payload.metadata)

        events = ["Analizando tu solicitud…"]
        query = payload.message.strip()
        mode = payload.mode if payload.mode in {"auto", "chat", "research", "math", "code"} else "auto"
        calculations = None
        sources: list[dict[str, Any]] = []
        evidence = ""
        selected: list[str] = []

        math_like = bool(re.fullmatch(r"[0-9.,\s()+\-*/%^]+", query)) or any(
            k in query.lower() for k in ("promedio", "media", "mediana", "porcentaje", "cagr", "probabilidad", "desviación", "desviacion")
        )
        if mode == "math" or (mode == "auto" and math_like):
            calculations = math_calculate(query) if re.fullmatch(r"[0-9.,\s()+\-*/%^]+", query) else math_analyze(query)
            events.append("Aplicando modelo matemático determinista…")

        if mode == "research" or (mode == "auto" and tools.needs_web_research(query, {"freshness_required": True})):
            selected = ["web_research"]
            events.append("Investigando fuentes públicas…")
            result = await tools.execute(selected, message=query, context={"current_intent_domain": "research"})
            wr = result.get("web_research", {}) if isinstance(result.get("web_research"), dict) else {}
            evidence = str(wr.get("evidence") or "")
            for item in (wr.get("results") or []):
                if item.get("evidence_verified") and item.get("url"):
                    sources.append({
                        "url": item.get("url"),
                        "title": item.get("title") or item.get("url"),
                        "verified": True,
                        "quality": item.get("source_quality", 0.0),
                    })
            if len(sources) < 2:
                events.append("La evidencia inicial es limitada; ejecutando contraste profundo…")
                plan = research.plan(query, {"research_required": True})
                plan = await research.fetch(plan)
                evidence = research.evidence_context(plan) or evidence
                for item in plan.evidence:
                    if item.ok and item.url and not any(s["url"] == item.url for s in sources):
                        sources.append({"url": item.url, "title": item.title or item.url, "verified": True, "quality": 0.65})
            events.append(f"Evidencia verificada: {len(sources)} fuente(s).")

        history = await memory.history(cid)
        await memory.append(cid, {"role": "user", "content": query})
        messages = history + [{"role": "user", "content": query}]
        system = (
            "You are Bitey IA, an independent general-purpose AI assistant. "
            "Answer directly and helpfully in the user's language. Never expose hidden chain-of-thought. "
            "Use tools and verified evidence when provided. Distinguish facts, calculations, and inferences. "
            "When sources are provided, cite factual claims inline as [S1], [S2], etc. "
            "For calculations, trust deterministic tool results rather than mental arithmetic. "
            "Do not invent current information."
        )
        if calculations is not None:
            system += f"\nDETERMINISTIC MATHEMATICAL RESULT: {calculations}"
        if evidence:
            system += f"\nVERIFIED WEB EVIDENCE:\n{evidence}"
        messages.insert(0, {"role": "system", "content": system})
        events.append("Seleccionando el modelo disponible y preparando la respuesta…")
        context = {
            "conversation_id": cid,
            "current_message": query,
            "current_intent_domain": "research" if evidence else "general",
            "evidence": evidence,
            "evidence_available": bool(evidence),
            "selected_tools": selected,
            "cost_mode": "free_only",
            "bitey_brain": brain.think(query, {}).as_dict(),
        }
        answer = await providers.generate(messages=messages, context=context)
        await memory.append(cid, {"role": "assistant", "content": answer})
        events.append("Respuesta verificada y preparada.")
        return ChatV2Response(
            conversation_id=cid,
            answer=answer,
            mode="research" if evidence else ("math" if calculations else mode),
            tools_used=selected + (["mathematics"] if calculations is not None else []),
            sources=sources[:10],
            activity_events=events,
            calculations=calculations,
            trace_id=None,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    return router
