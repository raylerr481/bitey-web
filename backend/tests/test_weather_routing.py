from app.core.tool_orchestrator import ToolOrchestrator


def test_weather_location_recovers_common_typo_and_known_city():
    orchestrator = ToolOrchestrator()
    assert orchestrator._weather_location("como esta el timepoe en Porto Alegre") == "porto alegre"
    assert orchestrator._weather_location("clima en São Paulo hoy") == "são paulo"


def test_weather_location_keeps_esteio_explicit():
    orchestrator = ToolOrchestrator()
    assert orchestrator._weather_location("temperatura actual en Esteio") == "esteio"
