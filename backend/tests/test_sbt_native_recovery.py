from backend.app.core.sbt_native_recovery import answer_from_sbt_evidence


def test_turtle_live_evidence_has_deterministic_fallback():
    evidence = (
        "SBT Turtle Controller verified from MT4 live snapshot. "
        "Symbol: EURUSD; timeframe: H1; signal: BUY; next_action: CHECK_RISK_GATE; "
        "position_count: 1; risk_pct: 0.25; drawdown_pct: 2.0; "
        "learning_status: OBSERVING; proposal_pending: False. Execution authority: SBT Risk Gate."
    )
    answer = answer_from_sbt_evidence(evidence)
    assert "EURUSD" in answer
    assert "BUY" in answer
    assert "Risk Gate" in answer


def test_turtle_no_snapshot_does_not_invent_state():
    evidence = "SBT Turtle Controller is reachable, but it has no current MT4 live snapshot."
    answer = answer_from_sbt_evidence(evidence)
    assert "no tiene una captura viva" in answer
    assert "señal" in answer


def test_sbt_ai_context_has_deterministic_fallback():
    evidence = (
        "SBT AI Bot Lab verified from MT4 context. "
        "Bot: Turtle EA; strategy: Turtle; symbol: EURUSD; timeframe: H1; mode: DEMO. "
    )
    answer = answer_from_sbt_evidence(evidence)
    assert "Turtle EA" in answer
    assert "Estrategia" in answer
    assert "EURUSD" in answer
