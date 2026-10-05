from app.chat_v2 import _objective_completion_gate


def test_objective_completion_requires_verification_for_evidence_task():
    result = _objective_completion_gate(
        goal="Investigar la información actual",
        plan_steps=[
            {"id": "retrieve", "status": "completed"},
            {"id": "verify", "status": "completed"},
        ],
        final_contract={
            "answer_present": True,
            "evidence_required": True,
            "evidence_available": True,
            "verification_completed": True,
            "ready": True,
        },
        answer_verification={"valid": True},
        evidence="verified source",
    )
    assert result["objective_status"] == "completed"
    assert result["replan_required"] is False


def test_objective_completion_replans_when_evidence_is_missing():
    result = _objective_completion_gate(
        goal="Investigar información actual",
        plan_steps=[{"id": "retrieve", "status": "failed"}],
        final_contract={
            "answer_present": True,
            "evidence_required": True,
            "evidence_available": False,
            "verification_completed": False,
            "ready": False,
        },
        answer_verification={"valid": False},
        evidence="",
    )
    assert result["objective_status"] == "partial"
    assert result["replan_required"] is True
    assert "verifiable_evidence" in result["missing_requirements"]


def test_objective_completion_never_trusts_agent_loop_flag_alone():
    result = _objective_completion_gate(
        goal="Completar investigación",
        plan_steps=[{"id": "retrieve", "status": "failed"}],
        final_contract={"answer_present": True, "evidence_required": True, "ready": False},
        answer_verification={"valid": False},
        evidence="",
        agent_loop={"objective_complete": True},
    )
    assert result["objective_status"] == "partial"
    assert result["replan_required"] is True


def test_objective_completion_blocker_waits_for_recovery():
    result = _objective_completion_gate(
        goal="Implementar la tarea",
        plan_steps=[{"id": "tool_execute", "status": "running"}],
        final_contract={"answer_present": True, "ready": False},
        answer_verification={"valid": False},
        evidence="",
        blockers=["provider_unavailable"],
    )
    assert result["objective_status"] == "blocked"
    assert result["replan_required"] is False
    assert result["next_action"].startswith("Resolver el bloqueo:")


def test_completed_objective_has_no_next_action():
    result = _objective_completion_gate(
        goal="Responder una pregunta estable",
        plan_steps=[{"id": "synthesize", "status": "completed"}],
        final_contract={
            "answer_present": True,
            "evidence_required": False,
            "verification_completed": True,
            "ready": True,
        },
        answer_verification={"valid": True},
        evidence="",
    )
    assert result["objective_status"] == "completed"
    assert result["next_action"] is None
