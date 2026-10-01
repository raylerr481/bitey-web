from app.core.bitey_brain import BiteyBrain
from app.core.executive_evaluator import ExecutiveEvaluator
from app.core.web_research_policy import WebResearchPolicy


def test_brain_keeps_stable_market_definition_direct():
    brain = BiteyBrain().think(
        "¿Qué es el mercado?",
        {
            "cognition": {
                "intention": {"domain": "general", "intent_family": "knowledge"},
                "perception": {"question": True, "greeting": False, "identity_request": False},
                "plan": {"needs_evidence": False},
            },
            "evidence_available": False,
        },
    )
    assert brain.task_class == "general"
    assert brain.conceptual_fallback is True
    assert brain.evidence_required is False
    assert brain.tool_priority == []


def test_web_policy_does_not_force_stable_conceptual_questions_to_research():
    policy = WebResearchPolicy()

    for query in (
        "¿Qué es un cohete?",
        "¿Qué es la NASA?",
        "¿Qué es el mercado?",
        "¿Qué significa inteligencia artificial?",
    ):
        decision = policy.decide(query)
        assert decision.required is False
        assert decision.strategy == "none"


def test_web_policy_keeps_dynamic_bitcoin_price_current():
    decision = WebResearchPolicy().decide("¿Cuál es el precio de Bitcoin ahora?")
    assert decision.required is True
    assert "freshness_sensitive" in decision.reasons
    assert "dynamic_domain" in decision.reasons


def test_conceptual_case_without_evidence_is_not_rejected_when_web_is_not_required():
    brain = {
        "task_class": "general",
        "evidence_required": False,
        "conceptual_fallback": True,
        "tool_priority": [],
        "risk_level": "low",
        "execution_allowed": True,
        "verification_required": False,
    }
    result = ExecutiveEvaluator().evaluate(
        state=brain,
        answer="Un cohete es un vehículo o dispositivo que genera empuje expulsando gases a gran velocidad.",
        evidence="",
        selected_tools=[],
    )
    assert result.decision in {"accept", "pass"}
