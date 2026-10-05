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
    assert selected == ["weather", "web_research"]


def test_weather_with_trading_terms_never_routes_to_sbt():
    selected = ToolOrchestrator().select("temperatura de BTCUSDT en Esteio", {})
    assert selected[0] == "weather"
    assert "sbt_market" not in selected


def test_arithmetic_uses_executable_calculator():
    selected = ToolOrchestrator().select("15% de 300", {})
    assert selected == ["calculator"]


def test_code_reasoning_is_not_a_phantom_tool():
    selected = ToolOrchestrator().select("escribe una función Python para ordenar una lista", {})
    assert "code_reasoning" not in selected
    assert all(name in {"web_research", "weather", "sbt_market", "calculator"} for name in selected)


def test_turtle_queries_route_to_sbt_turtle_read_model():
    selected = ToolOrchestrator().select("¿Qué está haciendo el Turtle ahora?", {})
    assert selected == ["sbt_turtle"]


def test_turtle_risk_queries_route_to_sbt_turtle():
    selected = ToolOrchestrator().select("¿Está bloqueado por el Risk Gate?", {})
    assert selected == ["sbt_turtle"]


def test_turtle_follow_up_reuses_turtle_context():
    selected = ToolOrchestrator().select(
        "¿Y ahora?",
        {"current_intent_domain": "trading", "selected_tools": ["sbt_turtle"]},
    )
    assert selected == ["sbt_turtle"]


def test_turtle_follow_up_without_context_does_not_hijack_general_chat():
    selected = ToolOrchestrator().select("¿Y ahora?", {})
    assert selected != ["sbt_turtle"]


def test_sbt_follow_up_reuses_general_sbt_context():
    selected = ToolOrchestrator().select(
        "¿Y ahora?",
        {"selected_tools": ["sbt_ai_context"]},
    )
    assert selected == ["sbt_ai_context"]


def test_sbt_follow_up_without_context_does_not_hijack_general_chat():
    selected = ToolOrchestrator().select("¿Y ahora?", {})
    assert selected != ["sbt_ai_context"]


def test_turtle_context_has_priority_over_general_sbt_context():
    selected = ToolOrchestrator().select(
        "¿Y ahora?",
        {"selected_tools": ["sbt_ai_context", "sbt_turtle"]},
    )
    assert selected == ["sbt_turtle"]


def test_sbt_follow_up_reuses_execution_context():
    selected = ToolOrchestrator().select(
        "¿Y ahora?",
        {"previous_execution_state": {"executed_tools": ["sbt_ai_context"]}},
    )
    assert selected == ["sbt_ai_context"]


def test_turtle_follow_up_reuses_execution_context_with_priority():
    selected = ToolOrchestrator().select(
        "¿Y ahora?",
        {
            "previous_execution_state": {
                "executed_tools": ["sbt_ai_context", "sbt_turtle"]
            }
        },
    )
    assert selected == ["sbt_turtle"]


def test_sbt_follow_up_reuses_persisted_result_context():
    selected = ToolOrchestrator().select(
        "¿Qué pasó?",
        {"sbt_context_active": True, "sbt_context_kind": "general"},
    )
    assert selected == ["sbt_ai_context"]


def test_turtle_follow_up_reuses_persisted_result_context():
    selected = ToolOrchestrator().select(
        "¿Y el equity?",
        {"sbt_context_active": True, "sbt_context_kind": "turtle"},
    )
    assert selected == ["sbt_turtle"]


def test_sbt_follow_up_reads_persisted_active_task_context():
    selected = ToolOrchestrator().select(
        "¿Y ahora?",
        {"active_task": {"sbt_context": {"active": True, "kind": "general"}}},
    )
    assert selected == ["sbt_ai_context"]


def test_turtle_follow_up_reads_persisted_active_task_context():
    selected = ToolOrchestrator().select(
        "¿Y ahora?",
        {"active_task": {"sbt_context": {"active": True, "kind": "turtle"}}},
    )
    assert selected == ["sbt_turtle"]
