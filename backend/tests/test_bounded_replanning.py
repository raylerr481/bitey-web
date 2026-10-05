from app.chat_v2 import _bounded_replan


def test_replanner_selects_unmet_step():
    result = _bounded_replan(
        objective_gate={
            "objective_status": "partial",
            "missing_requirements": ["verify"],
        },
        plan_steps=[
            {"id": "retrieve", "action": "Buscar", "status": "completed"},
            {"id": "verify", "action": "Verificar", "status": "pending"},
        ],
    )
    assert result["required"] is True
    assert result["next_action"]["id"] == "verify"


def test_replanner_does_not_repeat_same_replan():
    result = _bounded_replan(
        objective_gate={
            "objective_status": "partial",
            "missing_requirements": ["verify"],
        },
        plan_steps=[
            {"id": "verify", "action": "Verificar", "status": "pending"},
        ],
        previous_actions=["replan:verify"],
    )
    assert result["blocked"] is True
    assert result["next_action"]["kind"] == "blocked_wait"


def test_replanner_has_bounded_attempts():
    result = _bounded_replan(
        objective_gate={
            "objective_status": "partial",
            "missing_requirements": ["verify"],
        },
        plan_steps=[
            {"id": "verify", "action": "Verificar", "status": "pending"},
        ],
        previous_actions=["replan:a", "replan:b"],
        max_replans=2,
    )
    assert result["blocked"] is True
    assert result["reason"] == "replan_limit_reached"


def test_completed_objective_never_replans():
    result = _bounded_replan(
        objective_gate={"objective_status": "completed"},
        plan_steps=[{"id": "verify", "status": "pending"}],
    )
    assert result["required"] is False
    assert result["next_action"] is None
