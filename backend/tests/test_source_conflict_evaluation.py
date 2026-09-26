from app.core.bitey_brain import BiteyBrain
from app.core.evaluation_engine import verify_answer_claims
from app.core.executive_evaluator import ExecutiveEvaluator


def _state():
    return {
        "task_class": "general",
        "evidence_required": True,
        "tool_priority": ["web_research"],
        "risk_level": "low",
        "execution_allowed": False,
        "verification_required": False,
    }


def test_conflicting_verified_sources_require_acknowledgement():
    evaluator = ExecutiveEvaluator()
    evidence = (
        "SOURCE 1: https://a.example\nCONTENT: Population: 10\n"
        "SOURCE 2: https://b.example\nCONTENT: Population: 12"
    )
    result = evaluator.evaluate(
        state=_state(),
        answer="La población es 10.",
        evidence=evidence,
        selected_tools=["web_research"],
        conflict_detected=True,
    )
    assert result.decision == "revise"
    assert "source_conflict_not_acknowledged" in result.reasons


def test_conflicting_verified_sources_are_acknowledged():
    evaluator = ExecutiveEvaluator()
    evidence = (
        "SOURCE 1: https://a.example\nCONTENT: Population: 10\n"
        "SOURCE 2: https://b.example\nCONTENT: Population: 12"
    )
    result = evaluator.evaluate(
        state=_state(),
        answer="Las fuentes difieren: una indica 10 y otra 12. [S1] [S2]",
        evidence=evidence,
        selected_tools=["web_research"],
        conflict_detected=True,
    )
    assert result.decision == "accept"


def test_single_source_conflict_flag_is_not_required():
    evaluator = ExecutiveEvaluator()
    evidence = "SOURCE 1: https://a.example\nCONTENT: Population: 10"
    result = evaluator.evaluate(
        state=_state(),
        answer="La fuente consultada indica 10. [S1]",
        evidence=evidence,
        selected_tools=["web_research"],
        conflict_detected=False,
    )
    assert result.decision == "accept"


def test_unsupported_numeric_claim_is_rejected():
    evaluator = ExecutiveEvaluator()
    evidence = "SOURCE 1: https://a.example\nCONTENT: Population: 10"
    result = evaluator.evaluate(
        state=_state(),
        answer="La población es 25. [S1]",
        evidence=evidence,
        selected_tools=["web_research"],
    )
    assert result.decision == "revise"
    assert any(reason.startswith("unsupported_numeric_claim:") for reason in result.reasons)


def test_researched_general_answer_requires_source_reference():
    evaluator = ExecutiveEvaluator()
    evidence = "SOURCE 1: https://a.example\\nCONTENT: La población es 10."
    result = evaluator.evaluate(
        state=_state(),
        answer="La población es 10.",
        evidence=evidence,
        selected_tools=["web_research"],
    )
    assert result.decision == "revise"
    assert "research_claim_source_reference_missing" in result.reasons


def test_researched_general_answer_accepts_valid_source_reference():
    evaluator = ExecutiveEvaluator()
    evidence = "SOURCE 1: https://a.example\\nCONTENT: La población es 10."
    result = evaluator.evaluate(
        state=_state(),
        answer="La población es 10. [S1]",
        evidence=evidence,
        selected_tools=["web_research"],
    )
    assert result.decision == "accept"


def test_claim_verification_reports_atomic_support():
    evidence = (
        "SOURCE 1: https://a.example\\nCONTENT: La población es 10 millones.\\n"
        "SOURCE 2: https://b.example\\nCONTENT: La población creció 15% en 2025."
    )
    result = verify_answer_claims(
        "La población es 10 millones y creció 15% en 2025. [S1] [S2]",
        evidence=evidence,
    )
    statuses = [item["status"] for item in result["claim_details"]]
    assert "supported" in statuses
    assert result["unsupported_count"] == 0


def test_claim_verification_detects_unsupported_second_clause():
    evidence = "SOURCE 1: https://a.example\\nCONTENT: La población es 10 millones."
    result = verify_answer_claims(
        "La población es 10 millones y creció 15% en 2025. [S1]",
        evidence=evidence,
    )
    assert result["unsupported_count"] >= 1
    assert any(item["status"] == "unsupported" for item in result["claim_details"])


def test_claim_verification_keeps_uncited_inference_out_of_rejection():
    evidence = "SOURCE 1: https://a.example\\nCONTENT: La población es 10 millones."
    result = verify_answer_claims(
        "La población es 10 millones. Esto sugiere una tendencia estable.",
        evidence=evidence,
    )
    assert result["unsupported_count"] == 0
    assert result["skipped_claims"] >= 1


def test_brain_classifies_calculation_and_inference_profiles():
    brain = BiteyBrain()
    calculation = brain.think("¿Cuánto es 15% de 200?", {})
    assert "calculation" in calculation.verification_profile

    inference = brain.think("¿Qué significa que el mercado haya caído?", {})
    assert "inference" in inference.verification_profile


def test_brain_classifies_opinion_without_making_it_a_fact():
    brain = BiteyBrain()
    state = brain.think("¿Qué opinas sobre esta alternativa?", {})
    assert "opinion" in state.verification_profile
    assert "fact" in state.verification_profile


def test_compact_history_preserves_anchor_and_recent_turns():
    from app.chat_v2 import _compact_history

    history = [
        {"role": "user", "content": "Proyecto inicial"},
        {"role": "assistant", "content": "Contexto inicial"},
        {"role": "user", "content": "turno 2"},
        {"role": "assistant", "content": "turno 3"},
        {"role": "user", "content": "turno 4"},
        {"role": "assistant", "content": "turno 5"},
    ]
    selected = _compact_history(history, 4)
    assert selected[0]["content"] == "Proyecto inicial"
    assert [x["content"] for x in selected[-2:]] == ["turno 4", "turno 5"]
    assert len(selected) == 4


def test_compact_history_prioritizes_relevant_older_turn():
    from app.chat_v2 import _compact_history

    history = [
        {"role": "user", "content": "Proyecto Bitey IA"},
        {"role": "assistant", "content": "Contexto del proyecto"},
        {"role": "user", "content": "hablamos de cocina"},
        {"role": "assistant", "content": "receta"},
        {"role": "user", "content": "otros temas"},
        {"role": "assistant", "content": "respuesta"},
        {"role": "user", "content": "Bitey IA necesita memoria semántica"},
        {"role": "assistant", "content": "respuesta reciente"},
    ]
    selected = _compact_history(history, 6, "mejora la memoria semántica de Bitey IA")
    contents = [x["content"] for x in selected]
    assert "Proyecto Bitey IA" in contents
    assert "hablamos de cocina" not in contents
    assert "Bitey IA necesita memoria semántica" in contents
