from contextlib import asynccontextmanager
import asyncio
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .background_worker import process_once
from .core.context_engine import ContextEngine
from .core.deep_research import DeepResearchEngine
from .core.learning import LearningEngine
from .core.memory import MemoryStore
from .core.provider_gateway import ProviderGateway
from .core.research_engine import ResearchEngine
from .core.tool_orchestrator import ToolOrchestrator, ToolSpec, safe_calculate
from .core.workspace import WorkspaceStore
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

app = FastAPI(title="Bitey IA — Supracerebro Backend", version="0.8.0", description="General-purpose extensible intelligence with free-first tool and agent orchestration.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

context_engine = ContextEngine(); research_engine = ResearchEngine(); deep_research = DeepResearchEngine(); memory = MemoryStore(); providers = ProviderGateway(); workspace = WorkspaceStore(); learning = LearningEngine(); tools = ToolOrchestrator()

async def web_research_tool(message: str, context: dict | None = None) -> dict:
    plan = await deep_research.fetch(deep_research.plan(message, context or {}))
    return {"ok": True, "reasons": plan.reasons, "sources": deep_research.source_summary(plan), "evidence": deep_research.evidence_context(plan)}

async def workspace_files_tool(message: str, context: dict | None = None) -> dict:
    return {"ok": True, "available": True, "note": "Project files are handled through the general workspace layer."}

async def calculator_tool(message: str, context: dict | None = None) -> dict:
    import re
    matches = re.findall(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?:\s*[+\-*/%^]\s*[-+]?\d+(?:\.\d+)?)+", message)
    if not matches:
        return {"ok": True, "available": True, "calculated": False}
    try:
        return {"ok": True, "available": True, "calculated": True, "expression": matches[0], "result": safe_calculate(matches[0])}
    except Exception:
        return {"ok": False, "calculated": False, "error": "unsupported_expression"}

async def code_reasoning_tool(message: str, context: dict | None = None) -> dict:
    return {"ok": True, "available": True, "mode": "analysis_only", "note": "No arbitrary code execution is enabled by default."}

tools.register(ToolSpec("web_research", "Investiga fuentes públicas y recupera evidencia.", ("web", "research", "evidence"), web_research_tool))
tools.register(ToolSpec("workspace_files", "Usa archivos y proyectos como contexto general.", ("files", "projects"), workspace_files_tool))
tools.register(ToolSpec("calculator", "Calcula expresiones matemáticas de forma segura y local.", ("math",), calculator_tool))
tools.register(ToolSpec("code_reasoning", "Analiza código sin ejecutar código arbitrario.", ("code", "debug"), code_reasoning_tool))

@app.get("/health")
async def health() -> dict:
    return {"status":"ok","system":"bitey-ia-supracerebro","scope":"general_ai","supabase_persistence":memory.persistent,"workspace_persistence":workspace.persistent,"learning_persistence":learning.persistent,"background_cognitive_engine":True,"deep_research":True,"tool_orchestration":True}

@app.get("/api/v1/capabilities")
async def capabilities() -> dict:
    return {"conversation":True,"dynamic_context":True,"memory":True,"persistent_memory":memory.persistent,"projects":True,"project_files_metadata":True,"web_research":True,"deep_research":True,"web_search":True,"web_url_fetch":True,"feedback":True,"guarded_incremental_learning":learning.persistent,"background_cognitive_engine":True,"provider_orchestration":True,"tool_orchestration":True,"agent_orchestration":True,"tools":tools.available(),"cost_mode":"free_only","providers":providers.available()}

@app.post("/api/v1/conversations")
async def create_conversation(payload: ConversationCreate) -> dict:
    conversation_id=str(uuid4()); await memory.create_conversation(conversation_id,payload.metadata)
    project_id=payload.metadata.get("project_id")
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
    try: UUID(conversation_id)
    except ValueError: return MessageResponse(conversation_id=conversation_id,answer="La conversación indicada no tiene un identificador válido.",research_required=False,research_reasons=[],providers=providers.available())
    context=context_engine.assemble(message=payload.message,metadata=payload.metadata); ctx=context.as_dict()
    selected=tools.select(payload.message,ctx); tool_results=await tools.execute(selected,message=payload.message,context=ctx)
    plan=research_engine.plan(payload.message,ctx); deep_plan=deep_research.plan(payload.message,ctx)
    evidence=tool_results.get("web_research",{}).get("evidence","")
    if not evidence and (plan.required or deep_plan.reasons):
        deep_plan=await deep_research.fetch(deep_plan); evidence=deep_research.evidence_context(deep_plan)
    history=await memory.history(conversation_id); await memory.append(conversation_id,{"role":"user","content":payload.message}); messages=history+[{"role":"user","content":payload.message}]
    if evidence: messages.insert(0,{"role":"system","content":"TOOL EVIDENCE — información pública recuperada por Bitey. Usa evidencia, no inventes. Señala contradicciones y separa hechos de inferencias.\n\n"+evidence})
    elif plan.required or deep_plan.reasons: messages.insert(0,{"role":"system","content":"La investigación solicitada no recuperó evidencia utilizable. Decláralo y no inventes información."})
    answer=await providers.generate(messages=messages,context={**ctx,"selected_tools":selected,"tool_results":{k:{key:val for key,val in v.items() if key != "evidence"} if isinstance(v,dict) else v for k,v in tool_results.items()},"cost_mode":"free_only"})
    await memory.append(conversation_id,{"role":"assistant","content":answer})
    if learning.persistent: await learning.observe(title="conversation_observation",payload={"conversation_id":conversation_id,"message":payload.message,"answer":answer[:4000],"selected_tools":selected},source="conversation",confidence=.4)
    return MessageResponse(conversation_id=conversation_id,answer=answer,research_required=bool(plan.required or deep_plan.reasons),research_reasons=plan.reasons+[f"deep:{r}" for r in deep_plan.reasons],providers=providers.available())
