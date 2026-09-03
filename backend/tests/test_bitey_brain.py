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
