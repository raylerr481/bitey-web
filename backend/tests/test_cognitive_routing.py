from backend.app.core.cognitive_model import CognitiveModel


def _domain(message: str) -> str:
    state = CognitiveModel().process(message, {})
    return str(state.intention.get("domain"))


def test_weather_has_priority_over_trading_language():
    assert _domain("cual es la temperatura hoy en Esteio") == "weather"


def test_weather_typo_tolerance():
    assert _domain("cual e sal temperaturja hoy en esteio") == "weather"


def test_weather_time_query_is_not_trading():
    assert _domain("como esta el tiempo hoy en Esteio") == "weather"


def test_trading_remains_trading():
    assert _domain("analiza BTCUSDT ahora") == "trading"


def test_market_language_does_not_break_explicit_weather():
    assert _domain("temperatura y mercado hoy en Esteio") == "weather"


def test_generic_market_question_stays_general():
    assert _domain("qué es el mercado") == "general"


def test_generic_time_duration_stays_general():
    assert _domain("cuánto tiempo tarda") == "general"


def test_generic_client_question_stays_general():
    assert _domain("qué necesita un cliente") == "general"


def test_substantive_general_question_enters_evidence_first_loop():
    from backend.app.core.tool_orchestrator import ToolOrchestrator
    orchestrator = ToolOrchestrator()
    context = {}
    selected = orchestrator.cognitive_selection("qué es el mercado", context)
    assert "web_research" in selected["selected_tools"]
    assert selected["brain"]["evidence_required"] is True


def test_explicit_current_market_question_requires_web_evidence():
    from backend.app.core.tool_orchestrator import ToolOrchestrator
    assert ToolOrchestrator.needs_web_research("precio actual de BTCUSDT") is True



def test_native_architecture_keeps_generic_market_concept_general():
    from backend.app.core.cognitive_architecture import BiteyCognitiveArchitecture
    cognition = BiteyCognitiveArchitecture().run("¿Qué es el mercado?", {})
    assert cognition["frame"]["domain"] == "general"
    assert cognition["frame"]["intent"] == "answer_or_assist"
    assert cognition["decision"]["module"] is None


def test_native_architecture_keeps_trading_concept_general():
    from backend.app.core.cognitive_architecture import BiteyCognitiveArchitecture
    cognition = BiteyCognitiveArchitecture().run("¿Qué es trading?", {})
    assert cognition["frame"]["domain"] == "general"
    assert cognition["decision"]["module"] is None


def test_native_architecture_keeps_explicit_market_operation_trading():
    from backend.app.core.cognitive_architecture import BiteyCognitiveArchitecture
    cognition = BiteyCognitiveArchitecture().run("Analiza BTCUSDT en M1", {})
    assert cognition["frame"]["domain"] == "trading"
    assert cognition["decision"]["module"] == "sbt"


def test_brain_greeting_does_not_require_evidence():
    from backend.app.core.bitey_brain import BiteyBrain
    state = BiteyBrain().think("hola", {"cognition": {
        "intention": {"domain": "general"},
        "perception": {"greeting": True, "identity_request": False, "question": False},
        "plan": {"needs_evidence": False, "freshness_required": False},
    }})
    assert state.evidence_required is False
    assert state.tool_priority == []


def test_brain_conceptual_general_question_requires_evidence():
    from backend.app.core.bitey_brain import BiteyBrain
    state = BiteyBrain().think("qué es el mercado", {"cognition": {
        "intention": {"domain": "general"},
        "perception": {"greeting": False, "identity_request": False, "question": True},
        "plan": {"needs_evidence": False, "freshness_required": False},
    }})
    assert state.evidence_required is True
    assert "web_research" in state.tool_priority


def test_brain_current_market_operation_uses_sbt():
    from backend.app.core.bitey_brain import BiteyBrain
    state = BiteyBrain().think("precio actual de BTCUSDT", {"cognition": {
        "intention": {"domain": "trading"},
        "perception": {"greeting": False, "identity_request": False, "question": True},
        "plan": {"needs_evidence": True, "freshness_required": True},
    }})
    assert state.evidence_required is True
    assert state.tool_priority == ["sbt_market"]


def test_native_model_does_not_bypass_required_evidence():
    import asyncio
    from backend.app.core.native_model import NativeReasoningModel

    model = NativeReasoningModel()
    context = {"evidence_required": True, "research_required": True, "evidence": ""}
    answer = asyncio.run(model.generate(
        messages=[{"role": "user", "content": "¿Qué es el mercado?"}],
        context=context,
    ))

    assert "Un mercado es un sistema o espacio" not in answer
    assert "evidencia verificable suficiente" in answer

    
def test_orchestrator_normalizes_legacy_search_to_canonical_web_research():
    from backend.app.core.tool_orchestrator import ToolOrchestrator
    orchestrator = ToolOrchestrator()
    result = orchestrator.cognitive_selection("qué es el mercado", {})
    assert result["selected_tools"] == ["web_research"]

def test_web_research_preserves_verified_source_metadata(monkeypatch):
    import asyncio
    from backend.app.core.tool_orchestrator import ToolOrchestrator

    async def fake_search(self, message, context=None):
        return {
            "ok": True,
            "results": [{"url": "https://example.com/source", "evidence_verified": True, "page_evidence": "Population: 10"}],
            "evidence": "SOURCE 1: https://example.com/source\\nCONTENT: Population: 10",
            "verified_evidence_count": 1,
            "discovery_result_count": 1,
            "conflict_detected": True,
            "conflict_candidates": [{"field": "population", "values": ["10", "12"]}],
        }

    orchestrator = ToolOrchestrator()
    monkeypatch.setattr(orchestrator, "_search", fake_search.__get__(orchestrator, ToolOrchestrator))
    orchestrator._tools["web_research"] = orchestrator._tools["web_research"].__class__(
        "web_research", "test", ("web",), orchestrator._search
    )
    result = asyncio.run(orchestrator.execute(["web_research"], message="qué es el mercado", context={}))
    preserved = result["web_research"]
    assert preserved["verified_evidence_count"] == 1
    assert preserved["conflict_detected"] is True
    assert preserved["conflict_candidates"]

