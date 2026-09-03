from contextlib import asynccontextmanager
import asyncio
import time
from uuid import UUID, uuid4
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .background_worker import process_once
from .core.context_engine import ContextEngine
from .core.cognitive_memory import CognitiveMemoryAdapter
from .core.cognitive_model import CognitiveModel
from .core.bitey_brain import BiteyBrain
from .core.evaluation_engine import EvaluationEngine
from .core.module_registry import ModuleRegistry, ModuleSpec
from .core.deep_research import DeepResearchEngine
from .core.learning import LearningEngine
from .core.memory import MemoryStore
from .core.mongo_memory import MongoMemoryAdapter
from .core.neo4j_adapter import Neo4jAdapter
from .core.provider_gateway import ProviderGateway
from .core.research_engine import ResearchEngine
from .core.tool_orchestrator import ToolOrchestrator, ToolSpec, safe_calculate
from .core.vector_memory import QdrantVectorMemory
from .core.weather import WeatherEngine
from .core.workspace import WorkspaceStore
from .notifications import send_trainer_test_email
from .schemas import ConversationCreate, MessageCreate, MessageResponse

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
    await neo4j.close(); await mongo_memory.close(); await vector_memory.close()

app = FastAPI(title="Bitey IA — Cognitive Core", version="0.14.0", description="General-purpose extensible intelligence with autonomous language-driven capability orchestration, adaptive research, memory, knowledge, learning and evaluation.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

context_engine = ContextEngine(); cognition = CognitiveModel(); brain = BiteyBrain(); cognitive_memory = CognitiveMemoryAdapter(); evaluator = EvaluationEngine(); research_engine = ResearchEngine(); deep_research = DeepResearchEngine(); weather = WeatherEngine(); memory = MemoryStore(); mongo_memory = MongoMemoryAdapter(); neo4j = Neo4jAdapter(); vector_memory = QdrantVectorMemory(); providers = ProviderGateway(); workspace = WorkspaceStore(); learning = LearningEngine(); tools = ToolOrchestrator(); modules = ModuleRegistry()

modules.register(ModuleSpec("sbt", "Bitey IA integrated trading module for market intelligence, strategy and risk-aware workflows.", os.getenv("SBT_MODULE_URL"), ("trading", "market_intelligence", "strategy", "risk"), enabled=os.getenv("SBT_MODULE_ENABLED", "true").lower() != "false", metadata={"integration_type":"bitey_integrated","role":"integrated_specialized_module","owner":"bitey_ia","domain":"trading","execution_boundary":"sbt_risk_gate","live_trading":False}))
if os.getenv("BITEFIXES_MODULE_ENABLED", "false").lower() == "true":
    modules.register(ModuleSpec("bitefixes", "Specialized business/support module exposed through an external API contract.", os.getenv("BITEFIXES_MODULE_URL"), ("business_support", "crm", "tickets", "customer_context"), metadata={"integration_type":"external_specialized","role":"external_specialized_module","owner":"bitefixes","domain":"business_support"}))

async def web_research_tool(message: str, context: dict | None = None) -> dict:
    plan = await deep_research.fetch(deep_research.plan(message, context or {})); return {"ok": True, "reasons": plan.reasons, "sources": deep_research.source_summary(plan), "evidence": deep_research.evidence_context(plan)}
async def weather_tool(message: str, context: dict | None = None) -> dict:
    result = await weather.current(message); return {**result, "description": weather.describe(result)}
async def workspace_files_tool(message: str, context: dict | None = None) -> dict: return {"ok": True, "available": True, "note": "Project files are handled through the general workspace layer."}
async def calculator_tool(message: str, context: dict | None = None) -> dict:
    import re
    matches = re.findall(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?:\s*[+\-*/%^]\s*[-+]?\d+(?:\.\d+)?)+", message)
    if not matches: return {"ok": True, "available": True, "calculated": False}
    try: return {"ok": True, "available": True, "calculated": True, "expression": matches[0], "result": safe_calculate(matches[0])}
    except Exception: return {"ok": False, "calculated": False, "error": "unsupported_expression"}
async def code_reasoning_tool(message: str, context: dict | None = None) -> dict: return {"ok": True, "available": True, "mode": "analysis_only", "note": "No arbitrary code execution is enabled by default."}
tools.register(ToolSpec("web_research", "Investiga fuentes públicas y recupera evidencia.", ("web", "research", "evidence"), web_research_tool))
tools.register(ToolSpec("weather", "Obtiene meteorología actual mediante una fuente pública sin API key.", ("weather", "clima", "tiempo", "temperatura", "lluvia", "humedad", "pronóstico", "forecast"), weather_tool))
tools.register(ToolSpec("workspace_files", "Usa archivos y proyectos como contexto general.", ("files", "projects"), workspace_files_tool))
tools.register(ToolSpec("calculator", "Calcula expresiones matemáticas de forma segura y local.", ("math",), calculator_tool))
tools.register(ToolSpec("code_reasoning", "Analiza código sin ejecutar código arbitrario.", ("code", "debug"), code_reasoning_tool))

@app.get("/health")
async def health() -> dict: return {"status":"ok","system":"bitey-ia-cognitive-core","scope":"general_ai","version":"0.14.0","supabase_persistence":memory.persistent,"cognitive_memory_persistence":cognitive_memory.persistent,"mongo_memory":await mongo_memory.health(),"vector_memory":await vector_memory.health(),"workspace_persistence":workspace.persistent,"learning_persistence":learning.persistent,"neo4j":await neo4j.health(),"background_cognitive_engine":True,"deep_research":True,"adaptive_search":True,"weather":True,"tool_orchestration":True,"cognitive_model":True,"bitey_brain":brain.status(),"response_evaluator":True,"module_registry":True,"registered_modules":modules.names()}

@app.get("/api/v1/capabilities")
async def capabilities() -> dict: return {"conversation":True,"dynamic_context":True,"memory":True,"persistent_memory":memory.persistent,"cognitive_memory":True,"cognitive_memory_persistence":cognitive_memory.persistent,"projects":True,"project_files_metadata":True,"web_research":True,"deep_research":True,"web_search":True,"web_url_fetch":True,"adaptive_search":True,"weather":True,"feedback":True,"guarded_incremental_learning":learning.persistent,"background_cognitive_engine":True,"provider_orchestration":True,"tool_orchestration":True,"agent_orchestration":True,"cognitive_model":True,"bitey_brain":True,"response_evaluator":True,"evaluator_decisions":["accept","revise","reject"],"cognitive_stages":["perception","intention","context","memory","planning","evidence","reasoning","risk","decision","generation","evaluation","memory_learning"],"tools":tools.available(),"cost_mode":"free_only","providers":providers.available(),"modules":modules.available(),"module_registry":True}

@app.get("/api/v1/cognitive/status")
async def cognitive_status() -> dict: return {"architecture":"bitey-independent-cognitive-core","architecture_version":"1.4.0","executive_brain":brain.status(),"native_model_enabled":os.getenv("BITEY_NATIVE_MODEL_ENABLED","true").lower()=="true","evaluator_enabled":True,"memory_adapter_configured":cognitive_memory.persistent,"learning_persistence":learning.persistent,"provider_mode":"free_only","council_mode":"provider_failover_not_consensus","capability_orchestration":"language_driven_adaptive","memory_organs":{"supabase":memory.persistent,"mongodb":mongo_memory.configured,"neo4j":neo4j.configured,"qdrant":vector_memory.configured},"live_trading_enabled":False,"news_auto_execution":False,"modules":modules.names()}

@app.get("/api/v1/cognitive/brain")
async def cognitive_brain() -> dict: return brain.status()
@app.get("/api/v1/knowledge/status")
async def knowledge_status() -> dict: return {"owner":"bitey_ia","role":"cognitive_support_component","second_brain":False,"canonical_store":"supabase.bitey","neo4j":await neo4j.health(),"vector_memory":await vector_memory.health(),"graphrag_stage":"supabase_knowledge_graph_plus_optional_vector","vector_search_enabled":vector_memory.configured}
@app.get("/api/v1/knowledge/context")
async def knowledge_context(q: str) -> dict: return {"query":q,"source":"supabase.bitey","context":await neo4j.related_context(q)}
@app.get("/api/v1/modules")
async def module_catalog() -> dict: return {"owner":"bitey_ia","description":"Capability modules routed by Bitey Cognitive Core.","modules":modules.available()}
@app.get("/api/v1/modules/resolve/{domain}")
async def resolve_module(domain: str) -> dict:
    resolved = modules.resolve_for_domain(domain); return {"domain":domain,"selected":[{"name":m.name,"integration_type":m.integration_type,"role":m.role,"configured":bool(m.endpoint),"capabilities":list(m.capabilities)} for m in resolved]}
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
    context=context_engine.assemble(message=payload.message,metadata=payload.metadata); ctx=context.as_dict(); activity_events.append("Identificando intención y contexto…")
    learned_memory=await cognitive_memory.retrieve(payload.message,ctx); ctx["learned_cognitive_context"]={"summary":learned_memory.get("summary"),"counts":learned_memory.get("counts",{}),"available":learned_memory.get("available",False)}; learned_prompt=cognitive_memory.compact_for_prompt(learned_memory)
    graph_context=await neo4j.related_context(payload.message)
    if graph_context.get("available") and graph_context.get("results"): ctx["graph_context"]={"available":True,"count":graph_context.get("count",0),"results":graph_context.get("results",[])}
    selected=tools.select(payload.message,ctx); tool_results=await tools.execute(selected,message=payload.message,context=ctx)
    if selected: activity_events.append("Orquestando capacidades necesarias…")
    plan=research_engine.plan(payload.message,ctx); deep_plan=deep_research.plan(payload.message,{**ctx,"research":("web_research" in selected) or bool(ctx.get("external_information_required"))}); evidence=tool_results.get("web_research",{}).get("evidence","")
    if not evidence and (plan.required or deep_plan.reasons) and "web_research" not in selected: deep_plan=await deep_research.fetch(deep_plan); evidence=deep_research.evidence_context(deep_plan); activity_events.append("Investigando y contrastando información…")
    ctx["tool_results"]={k:{key:val for key,val in v.items() if key not in {"evidence"}} if isinstance(v,dict) else v for k,v in tool_results.items()}; ctx["evidence_available"]=bool(evidence); cognitive=cognition.process(payload.message,ctx,evidence_available=bool(evidence)); ctx["cognition"]=cognitive.as_dict(); brain_state=brain.think(payload.message,ctx); ctx["bitey_brain"]=brain_state.as_dict()
    domain=cognitive.intention.get("domain", "general"); resolved_modules=modules.resolve_for_domain(domain)
    history=await memory.history(conversation_id); await memory.append(conversation_id,{"role":"user","content":payload.message}); messages=history+[{"role":"user","content":payload.message}]
    system_context=[brain.system_directive(brain_state)]
    if learned_prompt: system_context.append("LEARNED COGNITIVE CONTEXT — advisory. Prioriza evidencia actual.\n\n"+learned_prompt)
    if graph_context.get("available") and graph_context.get("results"): system_context.append("KNOWLEDGE CONTEXT — contexto relacional de Supabase. Verifica cuando sea necesario.\n\n"+str(graph_context.get("results")))
    if tool_results.get("weather",{}).get("ok"): system_context.append("WEATHER TOOL RESULT — datos meteorológicos obtenidos por una capacidad externa autorizada. No digas que Bitey carece de acceso en tiempo real. Usa estos datos y su fuente.\n\n"+str(tool_results["weather"]))
    if evidence: system_context.append("TOOL EVIDENCE — información pública recuperada por Bitey. Usa evidencia, no inventes. Señala contradicciones.\n\n"+evidence)
    elif plan.required or deep_plan.reasons: system_context.append("La investigación solicitada no recuperó evidencia utilizable. Decláralo y no inventes información.")
    for system_message in reversed(system_context): messages.insert(0,{"role":"system","content":system_message})
    provider_context={**ctx,"conversation_id":conversation_id,"selected_tools":selected,"tool_results":tool_results,"cost_mode":"free_only"}; answer=await providers.generate(messages=messages,context=provider_context)
    evaluation=evaluator.evaluate(user_message=payload.message,answer=answer,context=ctx,evidence=evidence); ctx["evaluation"]=evaluation.as_dict();
    if evaluation.decision != "accept":
        answer=await providers.generate(messages=messages+[ {"role":"user","content":"Revisa tu respuesta según la evaluación cognitiva y corrige hechos, evidencia y uso de capacidades. No declares limitaciones que el orquestador no haya reportado."}],context={**provider_context,"revision":evaluation.as_dict()})
        evaluation=evaluator.evaluate(user_message=payload.message,answer=answer,context=ctx,evidence=evidence)
    await cognitive_memory.record_evaluation(await memory.get_session_id(conversation_id),payload.message,answer,evaluation.as_dict())
    await cognitive_memory.record_learning_event(await memory.get_session_id(conversation_id),"response_evaluation",str(evaluation.as_dict()),"accepted" if evaluation.decision=="accept" else "revised")
    await memory.append(conversation_id,{"role":"assistant","content":answer})
    return MessageResponse(conversation_id=conversation_id,answer=answer,research_required=bool(plan.required or deep_plan.reasons),research_reasons=list(dict.fromkeys(plan.reasons+deep_plan.reasons)),providers=providers.available(),elapsed_ms=int((time.perf_counter()-started)*1000),activity_events=activity_events)
