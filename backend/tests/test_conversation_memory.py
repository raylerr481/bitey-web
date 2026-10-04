from backend.app.chat_v2 import _detect_memory_updates, _structured_conversation_memory, _active_conversation_state


def test_superseded_preference_becomes_inactive():
    history = [{"role": "user", "content": "Prefiero trabajar con Python"}]
    updates = _detect_memory_updates(history, "Ahora prefiero trabajar con TypeScript en vez de Python")
    memory = _structured_conversation_memory(history, updates)
    assert updates["current_overrides"] is True
    assert memory["preferences"][0]["status"] == "superseded"


def test_unrelated_preference_stays_active():
    history = [
        {"role": "user", "content": "Prefiero trabajar con Python"},
        {"role": "user", "content": "Me gusta usar documentación clara"},
    ]
    updates = _detect_memory_updates(history, "Ahora prefiero trabajar con TypeScript en vez de Python")
    memory = _structured_conversation_memory(history, updates)
    statuses = {item["text"]: item["status"] for item in memory["preferences"]}
    assert statuses["Prefiero trabajar con Python"] == "superseded"
    assert statuses["Me gusta usar documentación clara"] == "active"


def test_memory_override_is_not_evidence():
    history = [{"role": "user", "content": "Quiero usar TypeScript desde ahora"}]
    memory = _structured_conversation_memory(history, {})
    assert memory["goals"][0]["status"] == "active"
    assert "evidence" not in memory["goals"][0]


def test_active_conversation_state_keeps_recent_turns_and_previous_result_context():
    history = [
        {"role": "user", "content": "Busca opciones de VPS gratuitos"},
        {"role": "assistant", "content": "Encontré tres opciones.", "metadata": {
            "reference_context": {"options": ["A", "B", "C"], "sources": [{"index": 1, "title": "Fuente A", "url": "https://example.com/a"}]}
        }},
        {"role": "user", "content": "¿Cuál es mejor?"},
        {"role": "assistant", "content": "La opción B parece mejor por el contexto anterior."},
    ]
    state = _active_conversation_state(history, {}, "¿Y la segunda?")
    assert state["last_user_request"] == "¿Cuál es mejor?"
    assert "opción B" in state["last_assistant_answer"]
    assert state["previous_result_context"]["options"] == ["A", "B", "C"]


def test_active_conversation_state_is_not_evidence():
    state = _active_conversation_state(
        [{"role": "user", "content": "¿Cuál es el precio actual de Bitcoin?"}],
        {},
        "¿Y Ethereum?",
    )
    assert state["trust"] == "continuity_only_not_evidence"
    assert state["last_user_request"]
    assert "evidence" not in state
