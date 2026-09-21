from app.core.executive_evaluator import ExecutiveEvaluator


def test_executive_rejects_unprovenanced_evidence():
    state = {"task_class": "general", "evidence_required": True, "tool_priority": ["web_research"]}
    result = ExecutiveEvaluator().evaluate(
        state=state,
        answer="El mercado es un sistema donde se intercambian bienes.",
        evidence="The model says this is true.",
        selected_tools=["web_research"],
    )
    assert result.passed is False
    assert "evidence_provenance_missing" in result.reasons


def test_executive_accepts_fetched_source_evidence():
    state = {"task_class": "general", "evidence_required": True, "tool_priority": ["web_research"]}
    result = ExecutiveEvaluator().evaluate(
        state=state,
        answer="La fuente recuperada describe el concepto solicitado. [S1]",
        evidence="SOURCE 1: https://example.com/article\nTITLE: Example\nCONTENT: Verified page content.",
        selected_tools=["web_research"],
    )
    assert result.passed is True
    assert result.evidence_compliant is True
