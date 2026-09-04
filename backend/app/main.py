from contextlib import asynccontextmanager
import asyncio
import time
from uuid import UUID, uuid4
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .background_worker import process_once
from .core.context_engine import ContextEngine
from .core.context_budget import build_context
from .core.cognitive_memory import CognitiveMemoryAdapter
from .core.cognitive_model import CognitiveModel
from .core.bitey_brain import BiteyBrain
from .core.cognitive_trace import CognitiveTraceStore
from .core.evaluation_engine import EvaluationEngine
from .core.module_registry import ModuleRegistry, ModuleSpec
from .core.deep_research import DeepResearchEngine
from .core.learning import LearningEngine
from .core.memory import MemoryStore
from .core.provider_gateway import ProviderGateway
from .core.research_engine import ResearchEngine
from .core.tool_orchestrator import ToolOrchestrator, ToolSpec, safe_calculate
from .core.vector_memory import QdrantVectorMemory
from .core.workspace import WorkspaceStore
from .notifications import send_trainer_test_email
from .schemas import ConversationCreate, MessageCreate, MessageResponse
from .workspace_api import router as workspace_router

async def _background_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try: await process_once()
        except Exception: pass
        try: await asyncio.wait_for(stop_event.wait(), timeout=60)
        except asyncio.TimeoutError: pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event(); task = asyncio.create_task(_background_loop(stop_event))
    app.state.background_stop = stop_event; app.state.background_task = task
    yield
    stop_event.set(); await task
    await vector_memory.close()

app = FastAPI(title="Bitey IA — Cognitive Core", version="0.15.0", description="General-purpose extensible intelligence with independent executive cognition, Supabase canonical memory, local Ollama inference, free-first model routing, general web search, evidence, learning and evaluation.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.include_router(workspace_router)

context_engine = ContextEngine(); cognition = CognitiveModel(); brain = BiteyBrain(); cognitive_trace = CognitiveTraceStore(); cognitive_memory = CognitiveMemoryAdapter(); evaluator = EvaluationEngine(); research_engine = ResearchEngine(); deep_research = DeepResearchEngine(); memory = MemoryStore(); vector_memory = QdrantVectorMemory(); providers = ProviderGateway(); workspace = WorkspaceStore(); learning = LearningEngine(); tools = ToolOrchestrator(); modules = ModuleRegistry()

modules.register(ModuleSpec("sbt", "Bitey IA integrated trading module for market intelligence, strategy and risk-aware workflows.", os.getenv("SBT_MODULE_URL"), ("trading", "market_intelligence", "strategy", "risk"), enabled=os.getenv("SBT_MODULE_ENABLED", "true").lower() != "false", metadata={"integration_type":"bitey_integrated","role":"integrated_specialized_module","owner":"bitey_ia","domain":"trading","execution_boundary":"sbt_risk_gate","live_trading":False}))

if os.getenv("BITEFIXES_MODULE_ENABLED", "false").lower() == "true":
    modules.register(ModuleSpec("bitefixes", "Specialized business/support module exposed through an external API contract.", os.getenv("BITEFIXES_MODULE_URL"), ("business_support", "crm", "tickets", "customer_context"), metadata={"integration_type":"external_specialized","role":"external_specialized_module","owner":"bitefixes","domain":"business_support"}))

async def web_research_tool(message: str, context: dict | None = None) -> dict:
    plan = await deep_research.fetch(deep_research.plan(message, context or {}))
    return {"ok": True, "reasons": plan.reasons, "sources": deep_research.source_summary(plan), "evidence": deep_research.evidence_context(plan)}
async def workspace_files_tool(message: str, context: dict | None = None) -> dict: return {"ok": True, "available": True, "note": "Project files are handled through the general workspace layer."}
async def calculator_tool(message: str, context: dict | None = None) -> dict:
    import re
    matches = re.findall(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?:\s*[+\-*/%^]\s*[-+]?\d+(?:\.\d+)?)+", message)
    if not matches: return {"ok": True, "available": True, "calculated": False}
    try: return {"ok": True, "available": True, "calculated": True, "expression": matches[0], "result": safe_calculate(matches[0])}
    except Exception: return {"ok": False, "calculated": False, "error": "unsupported_expression"}
async def code_reasoning_tool(message: str, context: dict | None = None) -> dict: return {"ok": True, "available": True, "mode": "analysis_only", "note": "No arbitrary code execution is enabled by default."}
tools.register(ToolSpec("web_research", "Investiga fuentes públicas y recupera evidencia mediante el motor de investigación.", ("web", "research", "evidence"), web_research_tool))
tools.register(ToolSpec("workspace_files", "Usa archivos y proyectos como contexto general.", ("files", "projects"), workspace_files_tool))
tools.register(ToolSpec("calculator", "Calcula expresiones matemáticas de forma segura y local.", ("math",), calculator_tool))
tools.register(ToolSpec("code_reasoning", "Analiza código sin ejecutar código arbitrario.", ("code", "debug"), code_reasoning_tool))

@app.get("/health")
async def health() -> dict:
    return {"status":"ok","system":"bitey-ia-cognitive-core","scope":"general_ai","version":"0.15.0","supabase_persistence":memory.persistent,"cognitive_memory_persistence":cognitive_memory.persistent,"vector_memory":await vector_memory.health(),"workspace_persistence":workspace.persistent,"learning_persistence":learning.persistent,"background_cognitive_engine":True,"deep_research":True,"general_search":"duckduckgo","tool_orchestration":True,"cognitive_model":True,"bitey_brain":brain.status(),"response_evaluator":True,"module_registry":True,"registered_modules":modules.names(),"ollama": "ollama-local" in providers.available(),"cognitive_trace":True}

@app.get("/api/v1/cognitive/traces/{trace_id}")
async def cognitive_trace_detail(trace_id: str) -> dict:
    trace = cognitive_trace.get(trace_id)
    if trace is None: return {"found":False,"trace_id":trace_id}
    return {"found":True,"trace":trace.snapshot()}

@app.get("/api/v1/cognitive/traces")
async def cognitive_trace_recent(conversation_id: str | None = None, limit: int = 20) -> dict:
    return {"traces":cognitive_trace.recent(conversation_id=conversation_id, limit=limit)}

@app.get("/api/v1/capabilities")
async def capabilities() -> dict:
    return {"conversation":True,"dynamic_context":True,"memory":True,"persistent_memory":memory.persistent,"cognitive_memory":True,"cognitive_memory_persistence":cognitive_memory.persistent,"semantic_vector_memory":vector_memory.configured,"projects":True,"project_files_metadata":True,"web_research":True,"deep_research":True,"web_search":True,"web_search_provider":"duckduckgo","web_url_fetch":True,"feedback":True,"guarded_incremental_learning":learning.persistent,"background_cognitive_engine":True,"provider_orchestration":True,"tool_orchestration":True,"agent_orchestration":True,"cognitive_model":True,"bitey_brain":True,"response_evaluator":True,"evidence_engine":True,"hypothesis_engine":True,"provenance":True,"context_selection":True,"context_budgeting":True,"evaluator_decisions":["accept","revise","reject"],"cognitive_stages":["perception","intention","context","memory","planning","evidence","hypothesis","reasoning","risk","decision","generation","evaluation","memory_learning"],"tools":tools.available(),"cost_mode":"free_only","providers":providers.available(),"modules":modules.available(),"module_registry":True,"free_registry":{"enabled":bool(os.getenv("OPENROUTER_API_KEY")) and os.getenv("OPENROUTER_ENABLED","false").lower() != "false","refresh_seconds":max(30,int(os.getenv("OPENROUTER_CATALOG_REFRESH_SECONDS","900")))},"email_notifications":bool(os.getenv('RESEND_API_KEY')),"cognitive_trace":True}

@app.get("/api/v1/cognitive/status")
async def cognitive_status() -> dict:
    return {"architecture":"bitey-independent-cognitive-core","architecture_version":"1.5.0","executive_brain":brain.status(),"native_model_enabled":os.getenv("BITEY_NATIVE_MODEL_ENABLED","true").lower()=="true","evaluator_enabled":True,"memory_adapter_configured":cognitive_memory.persistent,"learning_persistence":learning.persistent,"provider_mode":"free_only","council_mode":"local_first_provider_failover","search":{"provider":"duckduckgo","general":True,"specialized_weather":"open-meteo"},"reasoning_layers":{"evidence":True,"hypotheses":True,"provenance":True,"candidate_comparison":True,"context_budgeting":True},"memory_organs":{"supabase":memory.persistent,"qdrant":vector_memory.configured},"live_trading_enabled":False,"news_auto_execution":False,"modules":modules.names(),"cognitive_trace":True}

@app.get("/api/v1/cognitive/brain")
async def cognitive_brain() -> dict: return brain.status()
@app.get("/api/v1/knowledge/status")
async def knowledge_status() -> dict: return {"owner":"bitey_ia","role":"cognitive_support_component","second_brain":False,"canonical_store":"supabase","vector_memory":await vector_memory.health(),"semantic_search_enabled":vector_memory.configured}
@app.get("/api/v1/knowledge/context")
async def knowledge_context(q: str) -> dict:
    return {"query":q,"source":"supabase_cognitive_memory","context":await cognitive_memory.retrieve(q,{})}
@app.get("/api/v1/modules")
async def module_catalog() -> dict: return {"owner":"bitey_ia","description":"Capability modules routed by Bitey Cognitive Core.","modules":modules.available()}
@app.get("/api/v1/modules/resolve/{domain}")
async def resolve_module(domain: str) -> dict:
    resolved = modules.resolve_for_domain(domain); return {"domain":domain,"selected":[{"name":m.name,"integration_type":m.integration_type,"role":m.role,"configured":bool(m.endpoint),"capabilities":list(m.capabilities)} for m in resolved]}
@app.post("/api/v1/notifications/test-email")
async def test_email_notification() -> dict:
    result = await send_trainer_test_email(); return {"status":"sent","provider":"resend","id":result.get("id")}
@app.get("/api/v1/notifications/test-email-now")
async def test_email_notification_now() -> dict:
    result = await send_trainer_test_email(); return {"status":"sent","provider":"resend","id":result.get("id")}
@app.post("/api/v1/conversations")
async def create_conversation(payload: ConversationCreate) -> dict:
    conversation_id=str(uuid4()); await memory.create_conversation(conversation_id,payload.metadata); project_id=payload.metadata.get("project_id")
    if project_id: await workspace.attach_conversation(project_id,conversation_id)
    return {"conversation_id":conversation_id,"metadata":payload.metadata}
@app.get("/api/v1/projects")
async def list_projects() -> dict: return {"projects":await workspace.list_projects()}
@app.post("/api/v1/projects")
async def create_project(payload: dict) -> dict: return await workspace.create_project(name=str(payload.get("name") or "Nuevo proyecto"),description=str(payload.get("description") or ""),instructions=str(payload.get("instructions") or ""),metadata=payload.get("metadata") or {})
@app.post("/api/v1/projects/{project_id}/files")
async def register_project_file(project_id: str,payload: dict) -> dict: return await workspace.add_file_metadata(project_id=project_id,name=str(payload.get("name") or "archivo"),mime_type=payload.get("mime_type"),size_bytes=payload.get("size_bytes"),extracted_text=payload.get("extracted_text"),metadata=payload.get("metadata") or {})
@app.post("/api/v1/feedback")
async def submit_feedback(payload: dict) -> dict:
    await workspace.feedback(conversation_id=str(payload.get("conversation_id")),message_id=payload.get("message_id"),rating=payload.get("rating"),feedback=payload.get("feedback")); return {"status":"recorded"}

@app.post("/api/v1/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(conversation_id: str,payload: MessageCreate) -> MessageResponse:
    started=time.perf_counter(); activity_events=["Analizando tu solicitud…"]
    try: UUID(conversation_id)
    except ValueError: return MessageResponse(conversation_id=conversation_id,answer="La conversación indicada no tiene un identificador válido.",research_required=False,research_reasons=[],providers=providers.available(),elapsed_ms=int((time.perf_counter()-started)*1000),activity_events=["Validando la conversación…"])
    trace=cognitive_trace.start(payload.message,conversation_id,request_id=str(payload.metadata.get("request_id") or "") or None)
    ctx={}
    try:
        context=context_engine.assemble(message=payload.message,metadata=payload.metadata); ctx=context.as_dict(); activity_events.append("Identificando intención y contexto…")
        learned_memory=await cognitive_memory.retrieve(payload.message,ctx); ctx["learned_cognitive_context"]={"summary":learned_memory.get("summary"),"counts":learned_memory.get("counts",{}),"available":learned_memory.get("available",False)}; learned_prompt=cognitive_memory.compact_for_prompt(learned_memory)
        if learned_prompt: activity_events.append("Recuperando patrones cognitivos aprendidos desde Supabase…")
        selected=tools.select(payload.message,ctx); trace.tools={"selected":list(selected)}; tool_results=await tools.execute(selected,message=payload.message,context=ctx)
        if selected: activity_events.append("Consultando herramientas relevantes…")
        plan=research_engine.plan(payload.message,ctx); deep_plan=deep_research.plan(payload.message,ctx)
        evidence=tool_results.get("web_research",{}).get("evidence","")
        search_results=tool_results.get("search",{}).get("results",[])
        if search_results and not evidence:
            evidence="\n\n".join(f"SOURCE {i}: {item.get('url')}\nTITLE: {item.get('title','')}\nSNIPPET: {item.get('snippet','')}" for i,item in enumerate(search_results[:8],1))
        if not evidence and (plan.required or deep_plan.reasons): activity_events.append("Investigando y contrastando información…"); deep_plan=await deep_research.fetch(deep_plan); evidence=deep_research.evidence_context(deep_plan)
        trace.evidence={"available":bool(evidence),"required":bool(plan.required or deep_plan.reasons),"source_count":len(search_results),"research_reasons":plan.reasons+[f"deep:{r}" for r in deep_plan.reasons]}
        ctx["evidence_available"]=bool(evidence); cognitive=cognition.process(payload.message,ctx,evidence_available=bool(evidence)); ctx["cognition"]=cognitive.as_dict(); activity_events.append("Construyendo el razonamiento contextual…")
        brain_state=brain.think(payload.message,ctx); ctx["bitey_brain"]=brain_state.as_dict(); trace.decision={"intention":cognitive.intention,"domain":cognitive.intention.get("domain","general"),"reasoning_mode":brain_state.reasoning_mode,"model_role":brain_state.model_role,"risk_level":brain_state.risk_level,"plan":brain_state.plan,"goals":brain_state.goals,"constraints":brain_state.constraints,"tool_priority":brain_state.tool_priority,"decision_fingerprint":brain_state.decision_fingerprint}; activity_events.append(f"Bitey Brain: {brain_state.reasoning_mode}…")
        domain=cognitive.intention.get("domain", "general"); resolved_modules=modules.resolve_for_domain(domain)
        if resolved_modules: ctx["module_routing"]={"domain":domain,"selected":[m.name for m in resolved_modules],"integrated":[m.name for m in resolved_modules if m.integration_type == "bitey_integrated"]}; activity_events.append("Activando el módulo integrado de trading de Bitey…" if any(m.name == "sbt" for m in resolved_modules) else "Seleccionando el módulo especializado adecuado…")
        history=await memory.history(conversation_id); await memory.append(conversation_id,{"role":"user","content":payload.message}); messages=history+[{"role":"user","content":payload.message}]
        ctx["user_query"]=payload.message; ctx["current_message"]=payload.message; ctx["goals"]=brain_state.goals; ctx["constraints"]=brain_state.constraints; bounded_context=build_context("selected-provider",ctx)
        system_context=[brain.system_directive(brain_state)]
        system_context.append("BITEY COGNITIVE CONTRACT — Usa el contexto seleccionado y respeta sus límites. Modelos externos son motores de inferencia, no autoridades del sistema.")
        if learned_prompt: system_context.append("LEARNED COGNITIVE CONTEXT — patrones históricos/advisory almacenados en Supabase. No lo trates como verdad; prioriza evidencia actual y seguridad.\n\n"+learned_prompt)
        if evidence: system_context.append("TOOL EVIDENCE — información pública recuperada por Bitey. Usa evidencia, no inventes. Señala contradicciones y separa hechos de inferencias.\n\n"+evidence)
        elif plan.required or deep_plan.reasons: system_context.append("La investigación solicitada no recuperó evidencia utilizable. Decláralo y no inventes información.")
        for system_message in reversed(system_context): messages.insert(0,{"role":"system","content":system_message})
        activity_events.append("Seleccionando la mejor IA disponible…"); provider_context={**bounded_context,"conversation_id":conversation_id,"selected_tools":selected,"tool_results":{k:{key:val for key,val in v.items() if key != "evidence"} if isinstance(v,dict) else v for k,v in tool_results.items()},"cost_mode":"free_only"}; answer=await providers.generate(messages=messages,context=provider_context)
        trace.provider={"available":providers.available(),"selected":provider_context.get("provider_selected"),"model_role":brain_state.model_role,"executive_evaluation":provider_context.get("executive_evaluation"),"revision_attempted":bool(provider_context.get("executive_revision_attempted",False))}
        evaluation=evaluator.evaluate(user_message=payload.message,answer=answer,context=ctx,evidence=evidence); ctx["evaluation"]=evaluation.as_dict(); trace.evaluation={"generic":evaluation.as_dict(),"executive":provider_context.get("executive_evaluation")}; trace.revision={"attempted":bool(provider_context.get("executive_revision_attempted",False)),"executive":provider_context.get("executive_evaluation")}; activity_events.append(f"Evaluando respuesta: {evaluation.decision} ({evaluation.confidence:.2f})…")
        if evaluation.decision == "reject": answer="La respuesta generada no superó los controles internos de seguridad/calidad. No la presentaré como válida. Si quieres, puedo reformular la solicitud con evidencia y límites más precisos."
        elif evaluation.decision == "revise": answer += "\n\n_Nota de Bitey: esta respuesta queda sujeta a revisión por evidencia/confianza; verifica los puntos críticos antes de actuar._"
        await memory.append(conversation_id,{"role":"assistant","content":answer})
        if learning.persistent: await learning.observe(title="conversation_observation",payload={"conversation_id":conversation_id,"message":payload.message,"answer":answer[:4000],"selected_tools":selected,"cognitive_domain":domain,"cognitive_confidence":cognitive.confidence,"brain":brain_state.as_dict(),"selected_modules":[m.name for m in resolved_modules],"learned_context_available":learned_memory.get("available",False),"evaluation":evaluation.as_dict()},source="conversation",confidence=min(.8,max(.2,evaluation.confidence)))
        elapsed_ms=int((time.perf_counter()-started)*1000); cognitive_trace.finish(trace,evaluation.decision)
        return MessageResponse(conversation_id=conversation_id,answer=answer,research_required=bool(plan.required or deep_plan.reasons or search_results),research_reasons=plan.reasons+[f"deep:{r}" for r in deep_plan.reasons],providers=providers.available(),elapsed_ms=elapsed_ms,activity_events=activity_events)
    except Exception:
        cognitive_trace.finish(trace,"failed")
        raise
