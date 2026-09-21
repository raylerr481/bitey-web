from app.core.cognitive_architecture import BiteyCognitiveArchitecture


def test_market_definition_is_general():
    result = BiteyCognitiveArchitecture().run("¿Qué es el mercado?")
    assert result["frame"]["domain"] == "general"
    assert result["frame"]["intent"] == "answer_or_assist"
    assert result["decision"]["module"] is None


def test_trading_operation_remains_specialized():
    result = BiteyCognitiveArchitecture().run("Analiza BTCUSDT en M1")
    assert result["frame"]["domain"] == "trading"
    assert result["decision"]["module"] == "sbt"


def test_market_price_remains_specialized():
    result = BiteyCognitiveArchitecture().run("¿Cuál es el precio de BTCUSDT ahora?")
    assert result["frame"]["domain"] == "trading"
    assert result["decision"]["module"] == "sbt"


def test_weather_current_request_remains_weather():
    result = BiteyCognitiveArchitecture().run("¿Qué temperatura hay hoy?")
    assert result["frame"]["domain"] == "weather"
