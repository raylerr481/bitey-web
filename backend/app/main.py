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
    sources = deep_research.source_summary(plan)
    usable = [source for source in sources if source.get("ok") and source.get("url")]
    hosts = {
        urlparse(str(source.get("url") or "")).hostname.lower().removeprefix("www.")
        for source in usable
        if urlparse(str(source.get("url") or "")).hostname
    }
    return {
        "ok": bool(usable),
        "reasons": plan.reasons,
        "sources": sources,
        "results": [
            {
                **source,
                "evidence_verified": bool(source.get("ok")),
                "page_evidence": "",
                "source_quality": 0.65,
                "source_category": "web_source",
            }
            for source in usable
        ],
        "evidence": deep_research.evidence_context(plan),
        "verified_evidence_count": len(usable),
        "verified_source_host_count": len(hosts),
        "discovery_result_count": len(sources),
        "conflict_detected": False,
        "conflict_candidates": [],
    }
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