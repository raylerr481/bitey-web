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
from .core.workspace import WorkspaceStore
from .schemas import ConversationCreate, MessageCreate, MessageResponse


async def _background_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await process_once()
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    task = asyncio.create_task(_background_loop(stop_event))
    app.state.background_stop = stop_event
    app.state.background_task = task
    yield
    stop_event.set()
    await task


app = FastAPI(
    title="Bitey IA — Supracerebro Backend",
    version="0.6.0",
    description="Bitey IA with free-first orchestration, evidence-first deep research, memory, projects and guarded background learning.",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

context_engine = ContextEngine()
research_engine = ResearchEngine()
deep_research = DeepResearchEngine()
memory = MemoryStore()
providers = ProviderGateway()
workspace = WorkspaceStore()
learning = LearningEngine()


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {"status": "ok", "system": "bitey-ia-supracerebro", "supabase_persistence": memory.persistent, "workspace_persistence": workspace.persistent, "learning_persistence": learning.persistent, "background_cognitive_engine": True, "deep_research": True}


@app.get("/api/v1/capabilities")
async def capabilities() -> dict:
    return {"conversation": True, "dynamic_context": True, "memory": True, "persistent_memory": memory.persistent, "projects": True, "project_files_metadata": True, "web_research": True, "deep_research": True, "web_url_fetch": True, "feedback": True, "guarded_incremental_learning": learning.persistent, "background_cognitive_engine": True, "provider_orchestration": True, "cost_mode": "free_only", "providers": providers.available()}


@app.post("/api/v1/conversations")
async def create_conversation(payload: ConversationCreate) -> dict:
    conversation_id = str(uuid4())
    await memory.create_conversation(conversation_id, payload.metadata)
    project_id = payload.metadata.get("project_id")
    if project_id:
        await workspace.attach_conversation(project_id, conversation_id)
    return {"conversation_id": conversation_id, "metadata": payload.metadata}


@app.get("/api/v1/projects")
async def list_projects() -> dict:
    return {"projects": await workspace.list_projects()}


@app.post("/api/v1/projects")
async def create_project(payload: dict) -> dict:
    return await workspace.create_project(name=str(payload.get("name") or "Nuevo proyecto"), description=str(payload.get("description") or ""), instructions=str(payload.get("instructions") or ""), metadata=payload.get("metadata") or {})


@app.post("/api/v1/projects/{project_id}/files")
async def register_project_file(project_id: str, payload: dict) -> dict:
    return await workspace.add_file_metadata(project_id=project_id, name=str(payload.get("name") or "archivo"), mime_type=payload.get("mime_type"), size_bytes=payload.get("size_bytes"), extracted_text=payload.get("extracted_text"), metadata=payload.get("metadata") or {})


@app.post("/api/v1/feedback")
async def submit_feedback(payload: dict) -> dict:
    await workspace.feedback(conversation_id=str(payload.get("conversation_id")), message_id=payload.get("message_id"), rating=payload.get("rating"), feedback=payload.get("feedback"))
    return {"status": "recorded"}


@app.post("/api/v1/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(conversation_id: str, payload: MessageCreate) -> MessageResponse:
    try:
        UUID(conversation_id)
    except ValueError:
        return MessageResponse(conversation_id=conversation_id, answer="La conversación indicada no tiene un identificador válido.", research_required=False, research_reasons=[], providers=providers.available())

    context = context_engine.assemble(message=payload.message, metadata=payload.metadata)
    plan = research_engine.plan(payload.message, context.as_dict())
    deep_plan = deep_research.plan(payload.message, context.as_dict())
    deep_plan = await deep_research.fetch(deep_plan) if (plan.required or deep_plan.reasons) else deep_plan

    sources = await research_engine.fetch_urls(payload.message) if plan.required else []
    plan.sources = sources
    deep_context = deep_research.evidence_context(deep_plan)

    history = await memory.history(conversation_id)
    await memory.append(conversation_id, {"role": "user", "content": payload.message})
    messages = history + [{"role": "user", "content": payload.message}]

    if deep_context:
        messages.insert(0, {"role": "system", "content": "INVESTIGACIÓN PROFUNDA — evidencia pública recuperada. Usa esta evidencia como fuente primaria. No inventes hechos que no aparezcan en ella. Señala contradicciones y separa hechos de inferencias.\n\n" + deep_context})
    elif plan.required:
        usable = [s for s in sources if s.get("ok")]
        research_context = "\n\n".join(f"SOURCE: {item['url']}\nCONTENT: {item['content']}" for item in usable)
        if research_context:
            messages.insert(0, {"role": "system", "content": "INVESTIGACIÓN WEB — usa únicamente estas fuentes para hechos observados y no inventes contenido.\n\n" + research_context})
        elif plan.reasons:
            messages.insert(0, {"role": "system", "content": "La investigación web fue solicitada pero no se recuperó evidencia utilizable. Debes decirlo claramente y no rellenar con suposiciones."})

    answer = await providers.generate(messages=messages, context={**context.as_dict(), "research_plan": plan.__dict__, "deep_research": {"reasons": deep_plan.reasons, "sources": deep_research.source_summary(deep_plan)}, "cost_mode": "free_only"})
    await memory.append(conversation_id, {"role": "assistant", "content": answer})

    if learning.persistent:
        await learning.observe(title="conversation_observation", payload={"conversation_id": conversation_id, "message": payload.message, "answer": answer[:4000], "research_sources": deep_research.source_summary(deep_plan)}, source="conversation", confidence=0.4)

    return MessageResponse(conversation_id=conversation_id, answer=answer, research_required=plan.required, research_reasons=plan.reasons + [f"deep:{r}" for r in deep_plan.reasons], providers=providers.available())
