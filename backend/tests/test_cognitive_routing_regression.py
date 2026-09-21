from app.core.cognitive_architecture import BiteyCognitiveArchitecture


ARCHITECTURE = BiteyCognitiveArchitecture()


def test_conceptual_instrument_question_stays_general():
    result = ARCHITECTURE.run("¿Qué es BTCUSDT?")
    assert result["frame"]["domain"] == "general"
    assert result["decision"]["module"] is None


def test_temporal_word_does_not_hijack_conceptual_market_question():
    result = ARCHITECTURE.run("¿Qué es el mercado hoy?")
    assert result["frame"]["domain"] == "general"
    assert result["decision"]["module"] is None


def test_current_instrument_price_routes_to_sbt():
    result = ARCHITECTURE.run("¿Cuál es el precio de BTCUSDT ahora?")
    assert result["frame"]["domain"] == "trading"
    assert result["decision"]["module"] == "sbt"


def test_instrument_timeframe_analysis_routes_to_sbt():
    result = ARCHITECTURE.run("Analiza BTCUSDT en M1")
    assert result["frame"]["domain"] == "trading"
    assert result["decision"]["module"] == "sbt"


def test_temperature_question_routes_to_weather():
    result = ARCHITECTURE.run("¿Qué temperatura hay hoy?")
    assert result["frame"]["domain"] == "weather"
    assert result["decision"]["module"] == "weather"
