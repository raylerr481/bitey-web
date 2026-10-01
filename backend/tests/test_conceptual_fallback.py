from app.core.web_research_policy import WebResearchPolicy


def test_web_policy_does_not_force_stable_conceptual_questions_to_research():
    policy = WebResearchPolicy()

    for query in (
        "¿Qué es un cohete?",
        "¿Qué es la NASA?",
        "¿Qué es el mercado?",
        "¿Qué significa inteligencia artificial?",
    ):
        decision = policy.decide(query)
        assert decision.required is False
        assert decision.strategy == "none"


def test_web_policy_keeps_dynamic_bitcoin_price_current():
    decision = WebResearchPolicy().decide("¿Cuál es el precio de Bitcoin ahora?")
    assert decision.required is True
    assert "freshness_sensitive" in decision.reasons
    assert "dynamic_domain" in decision.reasons


def test_web_policy_detects_dynamic_market_context():
    for query in (
        "¿Cómo está el mercado ahora?",
        "¿Cuál es el valor actual del mercado?",
    ):
        decision = WebResearchPolicy().decide(query)
        assert decision.required is True
