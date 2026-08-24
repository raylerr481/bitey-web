from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.context_engine import ContextEngine
from .core.memory import MemoryStore
from .core.provider_gateway import ProviderGateway
from .core.research_engine import ResearchEngine
from .schemas import ConversationCreate, MessageCreate, MessageResponse

app = FastAPI(
    title="Bitey IA — Supracerebro Backend",
    version="0.3.0",
    description="General-purpose intelligence backend for Bitey IA.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

context_engine = ContextEngine()
research_engine = ResearchEngine()
memory = MemoryStore()
providers = ProviderGateway()


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "system": "bitey-ia-supracerebro",
        "supabase_persistence": memory.persistent,
    }


@app.get("/api/v1/capabilities")
async def capabilities() -> dict:
    return {
        "conversation": True,
        "dynamic_context": True,
        "memory": True,
        "persistent_memory": memory.persistent,
        "web_research_planning": True,
        "web_url_fetch": True,
        "enterprise_context": "optional",
        "provider_orchestration": True,
        "providers": providers.available(),
    }


@app.post("/api/v1/conversations")
async def create_conversation(payload: ConversationCreate) -> dict:
    conversation_id = str(uuid4())
    await memory.create_conversation(conversation_id, payload.metadata)
    return {"conversation_id": conversation_id, "metadata": payload.metadata}


@app.post("/api/v1/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(conversation_id: str, payload: MessageCreate) -> MessageResponse:
    try:
        UUID(conversation_id)
    except ValueError:
        return MessageResponse(
            conversation_id=conversation_id,
            answer="La conversación indicada no tiene un identificador válido.",
            research_required=False,
            research_reasons=[],
            providers=providers.available(),
        )

    context = context_engine.assemble(message=payload.message, metadata=payload.metadata)
    plan = research_engine.plan(payload.message, context.as_dict())
    sources = await research_engine.fetch_urls(payload.message) if plan.required else []
    plan.sources = sources

    history = await memory.history(conversation_id)
    await memory.append(conversation_id, {"role": "user", "content": payload.message})

    messages = history + [{"role": "user", "content": payload.message}]
    if sources:
        usable = [s for s in sources if s.get("ok")]
        research_context = "\n\n".join(
            f"SOURCE: {item['url']}\nCONTENT: {item['content']}" for item in usable
        )
        if research_context:
            messages.insert(0, {
                "role": "system",
                "content": (
                    "Bitey IA tiene acceso a investigación web explícita para esta consulta. "
                    "Usa las fuentes proporcionadas para responder; distingue hechos observados "
                    "de inferencias y no inventes contenido que no esté en las fuentes.\n\n"
                    + research_context
                ),
            })

    answer = await providers.generate(
        messages=messages,
        context={**context.as_dict(), "research_plan": plan.__dict__},
    )
    await memory.append(conversation_id, {"role": "assistant", "content": answer})

    return MessageResponse(
        conversation_id=conversation_id,
        answer=answer,
        research_required=plan.required,
        research_reasons=plan.reasons,
        providers=providers.available(),
    )
