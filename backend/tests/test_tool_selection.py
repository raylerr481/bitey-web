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
def test_weather_only_uses_specialized_tool():
    selected = ToolOrchestrator().select("cual es la temperatura hoy en Esteio", {})
    assert selected == ["weather"]


def test_weather_typo_still_uses_specialized_tool():
    selected = ToolOrchestrator().select("cual e sal temperaturja hoy en esteio", {})
    assert selected == ["weather"]


def test_weather_with_corroboration_uses_search_as_secondary():
    selected = ToolOrchestrator().select("temperatura hoy en Esteio, busca fuentes y corrobora", {})
    assert selected == ["weather", "search"]


def test_weather_with_trading_terms_never_routes_to_sbt():
    selected = ToolOrchestrator().select("temperatura de BTCUSDT en Esteio", {})
    assert selected[0] == "weather"
    assert "sbt_market" not in selected
