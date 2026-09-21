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
    assert "search" in selected["selected_tools"]
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
