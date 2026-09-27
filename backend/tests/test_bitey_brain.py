from app.core.bitey_brain import BiteyBrain


def test_complex_research_uses_evidence_first():
    brain = BiteyBrain()
    state = brain.think("Investiga y compara la arquitectura y verifica las fuentes actuales")
    assert state.evidence_required is True
    assert state.verification_required is True
    assert state.reasoning_mode == "evidence_first"
    assert "web_research" in state.tool_priority


def test_trading_action_is_critical_and_closed():
    state = BiteyBrain().think("ejecuta una orden real de trading", {"cognition": {"intention": {"domain": "trading"}}})
    assert state.risk_level == "critical"
    assert state.execution_allowed is False
    assert "no_live_execution" in state.constraints


def test_simple_request_stays_lightweight():
    state = BiteyBrain().think("Hola Bitey")
    assert state.reasoning_mode == "direct"
    assert state.risk_level == "low"


def test_current_requests_force_evidence_refresh():
    brain = BiteyBrain()
    state = brain.think(
        "¿Cuál es el precio actual de Bitcoin?",
        {
            "cognition": {"intention": {"domain": "finance"}, "perception": {"question": True}},
            "active_task": {
                "previous_execution_state": {
                    "executed_tools": ["web_research"],
                    "evidence_count": 3,
                }
            },
        },
    )
    retrieve = next(step for step in state.plan_steps if step["id"] == "retrieve")
    assert state.freshness_required is True
    assert retrieve["action"] == "refresh_current_evidence"


def test_stable_requests_can_reuse_prior_evidence_context():
    brain = BiteyBrain()
    state = brain.think(
        "Investiga qué es TCP/IP",
        {
            "cognition": {"intention": {"domain": "research"}, "perception": {"question": True}},
            "active_task": {
                "previous_execution_state": {
                    "executed_tools": ["web_research"],
                    "evidence_count": 3,
                }
            },
        },
    )
    retrieve = next(step for step in state.plan_steps if step["id"] == "retrieve")
    assert retrieve["action"] == "reuse_or_refresh_evidence"
