from types import SimpleNamespace

from app.core.executive_evaluator import ExecutiveEvaluator


def test_low_risk_reasoning_does_not_require_web_evidence():
    state = SimpleNamespace(
        task_class="general",
        evidence_required=False,
        conceptual_fallback=False,
        tool_priority=[],
        risk_level="low",
        execution_allowed=False,
        verification_required=True,
    )

    result = ExecutiveEvaluator().evaluate(
        state=state,
        answer="Una API REST usa HTTP para intercambiar recursos mediante operaciones como GET, POST, PUT y DELETE.",
        evidence="",
        selected_tools=[],
    )

    assert result.decision == "accept"
    assert result.verification_compliant is True
    assert "verification_requirement_not_satisfied" not in result.reasons


def test_evidence_required_still_requires_evidence():
    state = SimpleNamespace(
        task_class="research",
        evidence_required=True,
        conceptual_fallback=False,
        tool_priority=["web_research"],
        risk_level="low",
        execution_allowed=False,
        verification_required=True,
    )

    result = ExecutiveEvaluator().evaluate(
        state=state,
        answer="La información solicitada requiere datos actuales.",
        evidence="",
        selected_tools=[],
    )

    assert result.decision == "revise"
    assert result.evidence_compliant is False
    assert result.verification_compliant is False
