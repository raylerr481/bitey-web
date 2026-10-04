from backend.app.chat_v2 import _detect_memory_updates, _structured_conversation_memory, _active_conversation_state
from backend.app.core.conversation_context import build_conversation_context


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


def test_conversation_context_generalizes_beyond_weather():
    history = [
        {"role": "user", "content": "Compara estos VPS gratuitos"},
        {"role": "assistant", "content": "La opción B ofrece más recursos.", "metadata": {
            "reference_context": {"options": ["A", "B", "C"], "sources": [{"index": 1, "title": "Fuente A"}]}
        }},
    ]
    context = build_conversation_context(history, "¿Y la segunda?")
    assert context["continuation"] is True
    assert "segunda" in context["references"]
    assert context["topic"] == "comparison"
    assert context["previous_result_context"]["options"] == ["A", "B", "C"]
    assert context["trust"] == "continuity_only_not_evidence"
    assert context["evidence_source"] is False


def test_conversation_context_preserves_topic_for_short_followup():
    history = [
        {"role": "user", "content": "Explícame Docker y sus contenedores"},
        {"role": "assistant", "content": "Docker empaqueta aplicaciones en contenedores."},
    ]
    context = build_conversation_context(history, "¿Y la segunda parte?")
    assert context["continuation"] is True
    assert context["topic"] == "programming"
    assert context["last_user_request"] == "Explícame Docker y sus contenedores"


def test_active_conversation_state_exposes_generic_context_without_promoting_it_to_evidence():
    state = _active_conversation_state(
        [
            {"role": "user", "content": "¿Cuál es el precio actual de Bitcoin?"},
            {"role": "assistant", "content": "El precio actual debe verificarse."},
        ],
        {},
        "¿Y Ethereum?",
    )
    assert state["conversation_context"]["topic"] == "finance"
    assert state["conversation_context"]["continuation"] is True
    assert state["conversation_context"]["trust"] == "continuity_only_not_evidence"
    assert state["conversation_context"]["evidence_source"] is False
    assert "evidence" not in state["conversation_context"]


def test_conversation_context_detects_connector_and_entities_reliably():
    history = [
        {"role": "user", "content": "Investiga OpenAI y compara sus modelos con Anthropic."},
        {"role": "assistant", "content": "La comparación debe basarse en fuentes actuales."},
    ]
    context = build_conversation_context(history, "Y en Porto Alegre, ¿cuál conviene?")
    assert context["connector"] is True
    assert context["continuation"] is True
    assert any("Porto Alegre" in entity for entity in context["entities"])
    assert context["topic"] == "comparison"


def test_conversation_context_preserves_urls_as_references_not_evidence():
    history = [
        {"role": "user", "content": "Revisa https://example.com/docs y dime qué ofrece."},
        {"role": "assistant", "content": "La documentación describe varias funciones."},
    ]
    context = build_conversation_context(history, "¿Y esa página?")
    assert context["continuation"] is True
    assert "esa" in context["references"]
    assert context["entities"]
    assert context["evidence_source"] is False


def test_conversation_context_is_generic_across_domains_and_tracks_recent_topic():
    from backend.app.core.conversation_context import build_conversation_context

    history = [
        {"role": "user", "content": "Busca información sobre Python"},
        {"role": "assistant", "content": "Encontré información sobre Python."},
        {"role": "user", "content": "¿Y JavaScript?"},
        {"role": "assistant", "content": "También puedo comparar JavaScript."},
    ]
    context = build_conversation_context(history, "¿Y el segundo?", limit=4)
    assert context["continuation"] is True
    assert context["continuity_confidence"] in {"high", "medium"}
    assert context["topic"] in {"programming", "comparison"}
    assert "JavaScript" in context["recent_entities"] or "JAVASCRIPT" in context["recent_entities"]
    assert context["trust"] == "continuity_only_not_evidence"
    assert context["evidence_source"] is False


def test_conversation_context_keeps_current_request_above_old_topic():
    from backend.app.core.conversation_context import build_conversation_context

    history = [
        {"role": "user", "content": "¿Qué clima hay en Cuba?"},
        {"role": "assistant", "content": "Consulta meteorológica."},
    ]
    context = build_conversation_context(history, "Explícame Docker", limit=4)
    assert context["topic"] == "programming"
    assert context["topic_source"] == "current_request"
    assert context["evidence_source"] is False


def test_reference_resolution_maps_second_option_without_treating_it_as_evidence():
    history = [
        {"role": "user", "content": "Compara estos VPS gratuitos"},
        {"role": "assistant", "content": "Encontré tres opciones.", "metadata": {
            "reference_context": {"options": ["A", "B", "C"]}
        }},
    ]
    context = build_conversation_context(history, "¿Cuál es la segunda?")
    resolved = context["reference_resolution"]
    assert resolved["resolved"] is True
    assert resolved["target"]["kind"] == "previous_result_option"
    assert resolved["target"]["index"] == 2
    assert resolved["target"]["value"] == "B"
    assert resolved["evidence_source"] is False
    assert resolved["trust"] == "continuity_only_not_evidence"


def test_reference_resolution_handles_demonstrative_entity():
    history = [
        {"role": "user", "content": "Explícame Docker"},
        {"role": "assistant", "content": "Docker usa contenedores."},
    ]
    context = build_conversation_context(history, "¿Y eso cómo funciona?")
    resolved = context["reference_resolution"]
    assert resolved["resolved"] is True
    assert resolved["target"]["kind"] in {"recent_entity", "previous_turn"}
    assert resolved["evidence_source"] is False


def test_reference_resolution_handles_temporal_followup_without_changing_evidence_boundary():
    history = [
        {"role": "user", "content": "¿Qué clima hay en Cuba?"},
        {"role": "assistant", "content": "Consulta meteorológica."},
    ]
    context = build_conversation_context(history, "¿Y mañana?")
    assert context["temporal_context"] == ["mañana"]
    assert context["continuation"] is True
    assert context["reference_resolution"]["evidence_source"] is False


def test_reference_resolution_does_not_resolve_stale_old_option_for_new_topic():
    history = [
        {"role": "user", "content": "Compara estos VPS gratuitos"},
        {"role": "assistant", "content": "Encontré tres opciones.", "metadata": {
            "reference_context": {"options": ["A", "B", "C"]}
        }},
    ]
    context = build_conversation_context(history, "Explícame Python")
    assert context["topic"] == "programming"
    assert context["reference_resolution"]["resolved"] is False
    assert context["reference_resolution"]["uses_previous_result"] is False
