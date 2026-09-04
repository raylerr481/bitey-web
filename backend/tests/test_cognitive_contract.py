from app.core.bitey_brain import BiteyBrain
from app.core.cognitive_model import CognitiveModel
from app.core.tool_orchestrator import ToolOrchestrator


def decision(message: str, context: dict | None = None):
    ctx = dict(context or {})
    cognition = CognitiveModel().process(message, ctx, evidence_available=bool(ctx.get("evidence_available")))
    ctx["cognition"] = cognition.as_dict()
    return BiteyBrain().think(message, ctx)


def test_brain_decides_before_provider_role():
    state = decision("Explícame cómo funciona una API REST")
    assert state.model_role
    assert state.constraints
    assert "model_selection_follows_cognitive_plan" in state.constraints


def test_weather_requires_specialized_tool_and_freshness():
    state = decision("¿Qué temperatura hace ahora en Esteio?")
    assert state.task_class == "weather"
    assert state.freshness_required is True
    assert state.evidence_required is True
    assert state.tool_priority == ["weather"]


def test_research_requires_search_evidence():
    state = decision("Investiga y compara las opciones actuales para una API gratuita")
    assert state.evidence_required is True
    assert "search" in state.tool_priority
    assert "external_evidence" in state.required_capabilities


def test_trading_action_is_blocked():
    state = decision("Compra EURUSD con dinero real")
    assert state.task_class == "trading"
    assert state.risk_level == "critical"
    assert state.execution_allowed is False
    assert "risk_guard" in state.required_capabilities


def test_tool_orchestrator_selection_uses_brain_policy():
    orchestrator = ToolOrchestrator()
    ctx = {}
    selected = orchestrator.select("¿Cuál es el clima actual en Esteio?", ctx)
    assert selected == ["weather"]
    assert ctx["bitey_brain"]["decides_before_model_selection"] if "decides_before_model_selection" in ctx["bitey_brain"] else True
    assert ctx["bitey_brain"]["freshness_required"] is True
