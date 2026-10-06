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

    assert general["action"] == "ACTION_GENERAL"
    assert trading["action"] == "ACTION_TRADING"
    assert jobia["action"] == "ACTION_JOBIA"


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
