from backend.app.chat_v2 import _detect_memory_updates, _structured_conversation_memory


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
