from backend.app.core.cognitive_model import CognitiveModel


def _domain(message: str) -> str:
    state = CognitiveModel().process(message, {})
    return str(state.intention.get("domain"))


def test_weather_has_priority_over_trading_language():
    assert _domain("cual es la temperatura hoy en Esteio") == "weather"


def test_weather_typo_tolerance():
    assert _domain("cual e sal temperaturja hoy en esteio") == "weather"


def test_weather_time_query_is_not_trading():
    assert _domain("como esta el tiempo hoy en Esteio") == "weather"


def test_trading_remains_trading():
    assert _domain("analiza BTCUSDT ahora") == "trading"


def test_market_language_does_not_break_explicit_weather():
    assert _domain("temperatura y mercado hoy en Esteio") == "weather"


def test_generic_market_question_stays_general():
    assert _domain("qué es el mercado") == "general"


def test_generic_time_duration_stays_general():
    assert _domain("cuánto tiempo tarda") == "general"


def test_generic_client_question_stays_general():
    assert _domain("qué necesita un cliente") == "general"
