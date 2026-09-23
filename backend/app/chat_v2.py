from __future__ import annotations

import re
import time
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .core.bitey_brain import BiteyBrain
from .core.cognitive_trace import CognitiveTraceStore
from .core.deep_research import DeepResearchEngine
from .core.evaluation_engine import EvaluationEngine
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


def create_chat_v2_router(
    memory,
    providers: ProviderGateway,
    tools: ToolOrchestrator,
    brain: BiteyBrain,
    cognitive_trace: CognitiveTraceStore | None = None,
    evaluator: EvaluationEngine | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v2", tags=["chat"])
    research = DeepResearchEngine()
    trace_store = cognitive_trace or CognitiveTraceStore()
    response_evaluator = evaluator or EvaluationEngine()

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
            "evidence_gate": True,
            "evaluation_gate": True,
            "cognitive_trace": True,
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

        query = payload.message.strip()
        mode = payload.mode if payload.mode in {"auto", "chat", "research", "math", "code"} else "auto"
        request_id = str(payload.metadata.get("request_id") or "") or None
        trace = trace_store.start(query, cid, request_id=request_id)
        events: list[str] = []

        def emit(label: str) -> None:
            events.append(label)
            trace_store.emit(trace, label)

        emit("Analizando tu solicitud…")
        trace_store.set_stage(trace, "ANALYZING")
        calculations: dict[str, Any] | None = None
        sources: list[dict[str, Any]] = []
        evidence = ""
        selected: list[str] = []
        conflict_detected = False

        history = await memory.history(cid)
        ctx: dict[str, Any] = {
            "conversation_id": cid,
            "current_message": query,
            "request_id": request_id,
        }

        brain_state = brain.think(query, ctx)
        emit("Enrutando la solicitud según intención y capacidades…")
        ctx["bitey_brain"] = brain_state.as_dict()
        ctx["evidence_required"] = brain_state.evidence_required
        ctx["freshness_required"] = brain_state.freshness_required
        ctx["current_intent_domain"] = brain_state.task_class
        trace.decision = {
            "task_class": brain_state.task_class,
            "reasoning_mode": brain_state.reasoning_mode,
            "evidence_required": brain_state.evidence_required,
            "freshness_required": brain_state.freshness_required,
            "risk_level": brain_state.risk_level,
            "tool_priority": brain_state.tool_priority,
            "decision_fingerprint": brain_state.decision_fingerprint,
        }

        math_like = bool(re.fullmatch(r"[0-9.,\s()+\-*/%^]+", query)) or any(
            k in query.lower()
            for k in ("promedio", "media", "mediana", "porcentaje", "cagr", "probabilidad", "desviación", "desviacion")
        )

        if mode == "math" or (mode == "auto" and math_like):
            calculations = (
                math_calculate(query)
                if re.fullmatch(r"[0-9.,\s()+\-*/%^]+", query)
                else math_analyze(query)
            )
            emit("Aplicando cálculo determinista…")
            trace_store.set_stage(trace, "REASONING")

        # Explicit research always enters the evidence gate. Auto mode follows
        # the executive brain; chat mode remains conversational unless the
        # executive decision says fresh evidence is mandatory.
        research_required = mode == "research" or (
            mode == "auto" and (brain_state.evidence_required or tools.needs_web_research(query, ctx))
        )
        if mode == "chat":
            research_required = False

        if research_required and calculations is None:
            selected = ["web_research"]
            emit("Buscando información en la web…")
            result = await tools.execute(
                selected,
                message=query,
                context={
                    **ctx,
                    "current_intent_domain": brain_state.task_class,
                    "evidence_required": True,
                    "requires_web_research": True,
                },
            )
            wr = result.get("web_research", {}) if isinstance(result.get("web_research"), dict) else {}
            evidence = str(wr.get("evidence") or "")
            raw_sources = wr.get("sources") or wr.get("results") or []

            for item in raw_sources:
                if isinstance(item, dict) and item.get("ok") and item.get("url"):
                    sources.append({
                        "url": item.get("url"),
                        "title": item.get("title") or item.get("url"),
                        "verified": True,
                        "quality": item.get("source_quality", 0.65),
                    })

            if sources:
                emit(f"Encontradas {len(sources)} fuentes; verificando contenido…")
            else:
                emit("La búsqueda inicial no produjo fuentes verificables.")

            # Require corroboration for general research. If discovery produced
            # too little usable evidence, run the deep-research pass instead of
            # presenting search snippets as facts.
            distinct_hosts = {
                (str(source["url"]).split("/")[2] if "//" in str(source["url"]) else str(source["url"])).lower().removeprefix("www.")
                for source in sources
            }
            if not evidence or len(distinct_hosts) < (2 if brain_state.task_class in {"general", "research"} else 1):
                emit("Contrastando evidencia con una segunda pasada…")
                plan = research.plan(query, {"research_required": True, "current_intent_domain": brain_state.task_class})
                plan = await research.fetch(plan)
                deep_evidence = research.evidence_context(plan)
                if deep_evidence:
                    evidence = deep_evidence if not evidence else f"{evidence}\n\n{deep_evidence}"
                for item in plan.evidence:
                    if item.ok and item.url and not any(s["url"] == item.url for s in sources):
                        sources.append({
                            "url": item.url,
                            "title": item.title or item.url,
                            "verified": True,
                            "quality": 0.65,
                        })

            if sources:
                emit(f"Evidencia verificada: {len(sources)} fuente(s).")
            else:
                emit("No se pudo verificar evidencia suficiente; no se presentará como confirmada.")

        evidence_source_count = len(sources)
        ctx.update({
            "evidence": evidence,
            "evidence_available": bool(evidence),
            "evidence_source_count": evidence_source_count,
            "selected_tools": selected,
            "research_required": research_required,
            "evidence_attempted": bool(selected),
            "research_failure": research_required and not evidence,
            "evidence_conflict_detected": conflict_detected,
        })
        trace.tools = {"selected": selected}
        trace.evidence = {
            "available": bool(evidence),
            "required": research_required,
            "attempted": bool(selected),
            "source_count": evidence_source_count,
            "verified_sources": sources[:12],
            "conflict_detected": conflict_detected,
        }

        # Pure mathematical requests never pass through an LLM. This keeps
        # deterministic numeric results authoritative.
        if calculations is not None and (
            mode == "math" or bool(re.fullmatch(r"[0-9.,\s()+\-*/%^]+", query))
        ):
            if calculations.get("ok"):
                op = calculations.get("operation", "calculation")
                result = calculations.get("result")
                if op == "arithmetic":
                    answer = f"Resultado: {result}"
                elif op == "mean":
                    answer = f"Promedio: {result}"
                elif op == "median":
                    answer = f"Mediana: {result}"
                elif op == "percentage":
                    answer = f"Porcentaje: {result}%"
                elif op == "cagr":
                    answer = f"CAGR: {result * 100:.4f}%"
                elif op == "probability":
                    answer = f"Probabilidad: {result * 100:.4f}%"
                elif op == "sum":
                    answer = f"Suma: {result}"
                else:
                    answer = f"Resultado: {result}"
            else:
                answer = "No pude calcular esa expresión de forma segura. Reformúlala con una expresión matemática compatible."
            evaluation = response_evaluator.evaluate(
                user_message=query,
                answer=answer,
                context=ctx,
                evidence="",
                conflict_detected=False,
            )
        else:
            messages = history + [{"role": "user", "content": query}]
            system = (
                "You are Bitey IA, an independent general-purpose AI assistant. "
                "Answer directly and helpfully in the user's language. Never expose hidden chain-of-thought. "
                "Use verified evidence when provided. Distinguish facts, calculations, and inferences. "
                "When sources are provided, cite factual claims inline as [S1], [S2], etc. "
                "Do not invent current information. External model output is not evidence."
            )
            if evidence:
                system += f"\nVERIFIED WEB EVIDENCE:\n{evidence}"
                system += "\nUse only the numbered SOURCE entries present in the evidence and cite factual web claims with [S#]."
            elif research_required:
                system += "\nRESEARCH FAILURE: no usable evidence was verified. State that limitation and do not invent current facts."
            messages.insert(0, {"role": "system", "content": system})
            emit("Generando respuesta con el proveedor disponible…")
            trace_store.set_stage(trace, "GENERATING")
            provider_context = {
                **ctx,
                "cost_mode": "free_only",
                "evidence": evidence,
                "evidence_source_count": evidence_source_count,
            }
            answer = await providers.generate(messages=messages, context=provider_context)
            trace.provider = {
                "available": providers.available(),
                "selected": provider_context.get("provider_selected"),
            }
            emit("Evaluando respuesta…")
            evaluation = response_evaluator.evaluate(
                user_message=query,
                answer=answer,
                context=ctx,
                evidence=evidence,
                conflict_detected=conflict_detected,
            )

        ctx["evaluation"] = evaluation.as_dict()
        trace.evaluation = evaluation.as_dict()
        emit("Evaluando respuesta y controles de calidad…")
        trace_store.set_stage(trace, "EVALUATING")

        if evaluation.decision == "reject":
            answer = "La respuesta generada no superó los controles internos de seguridad/calidad. No la presentaré como válida."
        elif evaluation.decision == "revise":
            answer += "\n\n_Nota de Bitey: esta respuesta queda sujeta a revisión por evidencia/confianza; verifica los puntos críticos antes de actuar._"

        await memory.append(cid, {"role": "user", "content": query})
        await memory.append(cid, {"role": "assistant", "content": answer})
        trace_store.finish(trace, evaluation.decision)
        emit("Respuesta lista.")

        return ChatV2Response(
            conversation_id=cid,
            answer=answer,
            mode="research" if research_required else ("math" if calculations is not None else mode),
            tools_used=selected + (["mathematics"] if calculations is not None else []),
            sources=sources[:10],
            activity_events=events,
            calculations=calculations,
            trace_id=trace.trace_id,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    return router
