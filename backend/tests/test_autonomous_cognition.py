from app.core.autonomous_language_orchestrator import AutonomousLanguageOrchestrator
from app.core.contradiction_engine import ContradictionEngine
from app.core.tool_orchestrator import ToolOrchestrator


def test_weather_is_language_capability():
    plan = AutonomousLanguageOrchestrator().plan("¿Qué tiempo hace hoy en Esteio?")
    assert "weather" in plan.capabilities
    assert plan.external_information_required


def test_current_event_requires_research():
    plan = AutonomousLanguageOrchestrator().plan("¿Qué pasó hoy en Brasil?")
    assert "web_research" in plan.capabilities
    assert plan.freshness_required


def test_plain_explanation_does_not_force_web():
    plan = AutonomousLanguageOrchestrator().plan("Explícame cómo funciona DNS")
    assert "web_research" not in plan.capabilities


def test_contradiction_engine_detects_shared_numeric_claims():
    report = ContradictionEngine().inspect([
        {"url": "https://a.example", "ok": True, "content": "La cifra fue 25."},
        {"url": "https://b.example", "ok": True, "content": "La cifra fue 25."},
    ])
    assert report.evidence_count == 2
    assert report.contradiction_detected


def test_tool_router_uses_language_plan():
    router = ToolOrchestrator()
    router.register(type("T", (), {"name": "weather", "description": "", "capabilities": (), "handler": None})())
    plan = AutonomousLanguageOrchestrator().plan("¿Qué temperatura hay?").as_dict()
    assert router.select("¿Qué temperatura hay?", {"language_plan": plan}) == ["weather"]
