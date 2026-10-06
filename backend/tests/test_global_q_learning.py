import pytest

from app.core.q_learning import BiteyQLearning


@pytest.mark.asyncio
async def test_global_q_learning_keeps_domains_independent(monkeypatch):
    monkeypatch.setenv("BITEY_QLEARNING_ENABLED", "true")
    q = BiteyQLearning()
    q.url = ""
    q.key = ""

    domains = {
        "general": {"task_type": "answer"},
        "trading": {"symbol": "EURUSD", "timeframe": "M15", "strategy": "ENSEMBLE"},
        "jobia": {"job_type": "workflow"},
    }

    states = {}
    for domain, domain_context in domains.items():
        ctx = {
            "current_intent_domain": domain,
            "source": f"test_{domain}",
            "domain_context": domain_context,
        }
        states[domain] = q.state_for(ctx)
        await q.learn(ctx, action=f"ACTION_{domain.upper()}", reward=0.8)

    assert len(set(states.values())) == 3
    assert q.status["states"] == 3
    assert q.status["learned_pairs"] == 3

    general = q.choose(
        {"current_intent_domain": "general", "source": "test_general",
         "domain_context": domains["general"]},
        ["ACTION_GENERAL", "OTHER"],
    )
    trading = q.choose(
        {"current_intent_domain": "trading", "source": "test_trading",
         "domain_context": domains["trading"]},
        ["ACTION_TRADING", "OTHER"],
    )
    jobia = q.choose(
        {"current_intent_domain": "jobia", "source": "test_jobia",
         "domain_context": domains["jobia"]},
        ["ACTION_JOBIA", "OTHER"],
    )

    assert general["q_values"]["ACTION_GENERAL"] > general["q_values"]["OTHER"]
    assert trading["q_values"]["ACTION_TRADING"] > trading["q_values"]["OTHER"]
    assert jobia["q_values"]["ACTION_JOBIA"] > jobia["q_values"]["OTHER"]
    assert general["action"] in {"ACTION_GENERAL", "OTHER"}
    assert trading["action"] in {"ACTION_TRADING", "OTHER"}
    assert jobia["action"] in {"ACTION_JOBIA", "OTHER"}


@pytest.mark.asyncio
async def test_global_q_learning_preserves_sbt_safety_boundary():
    q = BiteyQLearning()
    q.url = ""
    q.key = ""

    ctx = {
        "current_intent_domain": "trading",
        "source": "bitey_sbt",
        "sbt": {
            "symbol": "EURUSD",
            "timeframe": "M15",
            "risk_gate_allowed": True,
            "operational_capital_usd": 500.0,
        },
    }
    result = await q.learn(ctx, action="ENSEMBLE", reward=1.0)
    assert -1.0 <= result["reward"] <= 1.0
    assert result["action"] == "ENSEMBLE"

    decision = q.choose(ctx, ["ENSEMBLE", "HOLD"])
    assert decision["action"] in {"ENSEMBLE", "HOLD"}
    assert decision["action"] != "NEW_UNAUTHORIZED_ACTION"


def test_trading_reward_prefers_profit_and_penalizes_excess_risk():
    q = BiteyQLearning()
    low_risk_win = q.trading_reward(pnl_usd=25.0, drawdown_pct=1.0, risk_used_pct=0.25)
    high_risk_same_win = q.trading_reward(pnl_usd=25.0, drawdown_pct=1.0, risk_used_pct=2.0)
    loss = q.trading_reward(pnl_usd=-25.0, drawdown_pct=3.0, risk_used_pct=0.25)

    assert 0.0 < low_risk_win <= 1.0
    assert high_risk_same_win < low_risk_win
    assert loss < 0.0

def test_trading_reward_uses_real_pnl_when_no_risk_telemetry():
    q = BiteyQLearning()
    assert q.trading_reward(pnl_usd=26.50) == q.normalize_reward(26.50 / 50.0)
    assert q.trading_reward(pnl_usd=-26.50) < 0.0
