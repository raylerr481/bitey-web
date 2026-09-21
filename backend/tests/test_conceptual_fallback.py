from app.core.bitey_brain import BiteyBrain
from app.core.executive_evaluator import ExecutiveEvaluator


def test_brain_marks_market_definition_as_research_required_conceptual_case():
    brain = BiteyBrain().think(
        "¿Qué es el mercado?",
        {
            "cognition": {
                "intention": {"domain": "general"},
                "perception": {"question": True, "greeting": False, "identity_request": False},
                "plan": {"needs_evidence": True},
            },
            "requires_web_research": True,
            "evidence_available": False,
        },
    )
    assert brain.task_class == "general"
    assert brain.conceptual_fallback is True
    assert brain.tool_priority == ["search"]


def test_conceptual_case_without_evidence_is_rejected():
    brain = {
        "task_class": "general",
        "evidence_required": True,
        "conceptual_fallback": True,
        "tool_priority": ["search"],
        "risk_level": "low",
        "execution_allowed": False,
        "verification_required": True,
    }
    result = ExecutiveEvaluator().evaluate(
        state=brain,
        answer="Un mercado es un sistema donde compradores y vendedores intercambian bienes, servicios o activos.",
        evidence="",
        selected_tools=["search"],
    )
    assert result.decision == "revise"
    assert "required_evidence_missing" in result.reasons
