from backend.app.core.tool_orchestrator import ToolOrchestrator


def test_weather_tool_selection_cannot_be_hijacked_by_trading():
    selected = ToolOrchestrator().select("cual es la temperatura hoy en Esteio", {})
    assert selected[0] == "weather"
    assert "sbt_market" not in selected


def test_weather_typo_tool_selection():
    selected = ToolOrchestrator().select("cual e sal temperaturja hoy en esteio", {})
    assert selected[0] == "weather"
    assert "sbt_market" not in selected


def test_trading_tool_selection_still_works():
    selected = ToolOrchestrator().select("analiza BTCUSDT ahora", {})
    assert selected[0] == "sbt_market"
