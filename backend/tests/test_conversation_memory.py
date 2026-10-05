from backend.app.chat_v2 import _detect_memory_updates, _structured_conversation_memory, _active_conversation_state
from backend.app.core.conversation_context import build_conversation_context\nfrom backend.app.chat_v2 import _active_task_state, _classify_task_lifecycle, _task_controller_decision


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


def test_active_task_resumes_from_reference_followup():
    history = [
        {"role": "user", "content": "Quiero comparar estos tres VPS"},
        {"role": "assistant", "content": "Comparé tres opciones.", "metadata": {
            "active_task_state": {
                "active": True,
                "goal": ["Quiero comparar estos tres VPS"],
                "constraints": ["Sin opciones de pago"],
                "last_decisions": ["Priorizar recursos"],
                "progress": {"completed": ["retrieve"]},
                "plan_steps": [{"id": "retrieve", "status": "completed"}, {"id": "verify", "status": "pending"}],
                "execution_state": {"execution_phase": "verify"}
            },
            "reference_context": {"options": ["A", "B", "C"]}
        }},
    ]
    updates = _detect_memory_updates(history, "¿Y la segunda?")
    state = _active_conversation_state(history, updates, "¿Y la segunda?")
    task = _active_task_state(history, "¿Y la segunda?", state)
    assert task["active"] is True
    assert task["continuation_detected"] is True


def test_active_task_accepts_common_continuation_typo_without_fuzzy_matching():
    history = [
        {"role": "user", "content": "Quiero mejorar Bitey IA"},
        {"role": "assistant", "content": "Detecté una mejora pendiente."},
    ]
    state = _active_conversation_state(history, {}, "conotua")
    task = _active_task_state(history, "conotua", state)
    assert task["continuation_detected"] is True
    assert task["active"] is True


def test_active_task_does_not_treat_unrelated_word_as_continuation():
    history = [
        {"role": "user", "content": "Quiero mejorar Bitey IA"},
        {"role": "assistant", "content": "Detecté una mejora pendiente."},
    ]
    state = _active_conversation_state(history, {}, "consulta sobre Bitcoin")
    task = _active_task_state(history, "consulta sobre Bitcoin", state)
    assert task["continuation_detected"] is False


def test_active_task_marks_persisted_work_as_available_on_continuation():
    history = [
        {"role": "user", "content": "Quiero mejorar el flujo de Bitey IA"},
        {"role": "assistant", "content": "Hay una mejora pendiente.", "metadata": {
            "active_task_state": {
                "active": True,
                "goal": ["Quiero mejorar el flujo de Bitey IA"],
                "progress": {"completed": 2, "total": 4, "ratio": 0.5},
                "plan_steps": [
                    {"id": "analyze", "status": "completed"},
                    {"id": "verify", "status": "pending"},
                ],
            }
        }},
    ]
    state = _active_conversation_state(history, {}, "continúa")
    task = _active_task_state(history, "continúa", state)
    assert task["continuation_detected"] is True
    assert task["persisted_task_available"] is True
    assert task["active"] is True



def test_task_lifecycle_pending_selects_first_real_action():
    lifecycle = _classify_task_lifecycle([
        {"id": "analyze", "action": "Analizar", "status": "completed"},
        {"id": "verify", "action": "Verificar resultados", "status": "pending"},
        {"id": "respond", "action": "Responder", "status": "pending"},
    ])
    assert lifecycle["task_status"] == "pending"
    assert lifecycle["next_action"]["id"] == "verify"
    assert lifecycle["next_action"]["kind"] == "next_pending"
    assert lifecycle["completed_phases"] == ["analyze"]


def test_task_lifecycle_running_continues_current_phase():
    lifecycle = _classify_task_lifecycle([
        {"id": "retrieve", "action": "Consultar fuentes", "status": "running"},
        {"id": "verify", "action": "Verificar", "status": "pending"},
    ])
    assert lifecycle["task_status"] == "running"
    assert lifecycle["current_phase"] == "retrieve"
    assert lifecycle["next_action"]["id"] == "retrieve"
    assert lifecycle["next_action"]["kind"] == "continue_running"


def test_task_lifecycle_blocked_selects_unblock_action():
    lifecycle = _classify_task_lifecycle([
        {
            "id": "deploy",
            "action": "Desplegar",
            "status": "blocked",
            "blockers": ["Falta una variable de entorno"],
            "unblock_action": "Configurar la variable de entorno",
        },
        {"id": "verify", "action": "Verificar despliegue", "status": "pending"},
    ])
    assert lifecycle["task_status"] == "blocked"
    assert lifecycle["next_action"]["kind"] == "unblock"
    assert lifecycle["next_action"]["id"] == "deploy"
    assert "Falta una variable de entorno" in lifecycle["blockers"]


def test_task_lifecycle_completed_never_selects_old_analysis_again():
    lifecycle = _classify_task_lifecycle([
        {"id": "analyze", "action": "Analizar", "status": "completed"},
        {"id": "verify", "action": "Verificar", "status": "completed"},
        {"id": "respond", "action": "Responder", "status": "completed"},
    ])
    assert lifecycle["task_status"] == "completed"
    assert lifecycle["next_action"] is None
    assert lifecycle["progress_ratio"] == 1.0


def test_task_lifecycle_is_not_evidence():
    lifecycle = _classify_task_lifecycle([
        {"id": "verify", "action": "Verificar", "status": "pending"},
    ])
    assert lifecycle["trust"] == "continuity_only_not_evidence"
    assert lifecycle["evidence_source"] is False


def test_task_controller_executes_the_next_action_instead_of_the_word_continua():
    active_task = {
        "continuation_detected": True,
        "goal": ["Investiga las mejores opciones de VPS gratuitos"],
        "task_lifecycle": {
            "task_status": "pending",
            "next_action": {
                "id": "retrieve",
                "action": "Consultar fuentes actuales",
                "kind": "next_pending",
            },
        },
        "previous_plan": [
            {"id": "retrieve", "action": "Consultar fuentes actuales", "status": "pending"}
        ],
    }
    decision = _task_controller_decision(active_task, type("Brain", (), {"plan_steps": []})(), "continúa")
    assert decision["action"] == "start"
    assert decision["step_id"] == "retrieve"
    assert decision["execution_message"] == "Investiga las mejores opciones de VPS gratuitos"
    assert decision["tool_override"] == ["web_research"]
    assert decision["trust"] == "continuity_only_not_evidence"
    assert decision["evidence_source"] is False


def test_task_controller_resumes_running_step():
    active_task = {
        "continuation_detected": True,
        "goal": ["Analiza el código de Bitey"],
        "task_lifecycle": {
            "task_status": "running",
            "next_action": {
                "id": "analyze",
                "action": "Analizar código",
                "kind": "continue_running",
            },
        },
        "previous_plan": [
            {"id": "analyze", "action": "Analizar código", "status": "running"}
        ],
    }
    decision = _task_controller_decision(active_task, type("Brain", (), {"plan_steps": []})(), "conitua")
    assert decision["action"] == "resume"
    assert decision["tool_override"] == ["code_reasoning"]


def test_task_controller_does_not_restart_completed_task():
    active_task = {
        "continuation_detected": True,
        "task_lifecycle": {"task_status": "completed", "next_action": None},
        "previous_plan": [],
    }
    decision = _task_controller_decision(active_task, type("Brain", (), {"plan_steps": []})(), "continúa")
    assert decision["action"] == "complete"
    assert decision["tool_override"] == []


def test_task_controller_blocked_step_uses_unblock_action_without_promoting_it_to_evidence():
    active_task = {
        "continuation_detected": True,
        "goal": ["Desplegar la aplicación"],
        "task_lifecycle": {
            "task_status": "blocked",
            "next_action": {
                "id": "deploy",
                "action": "Resolver el bloqueo",
                "kind": "unblock",
            },
        },
        "previous_plan": [
            {
                "id": "deploy",
                "action": "Desplegar",
                "status": "blocked",
                "unblock_action": "Revisar la configuración",
            }
        ],
    }
    decision = _task_controller_decision(active_task, type("Brain", (), {"plan_steps": []})(), "continúa")
    assert decision["action"] == "unblock"
    assert decision["execution_message"] == "Revisar la configuración"
    assert decision["evidence_source"] is False


def test_task_controller_failed_outcome_is_not_treated_as_progress():
    # Controller decisions themselves are continuity metadata; a failed
    # verification must be represented by the caller as blocked, never completed.
    active_task = {
        "continuation_detected": True,
        "goal": ["Verifica una afirmación"],
        "task_lifecycle": {
            "task_status": "running",
            "next_action": {"id": "verify", "action": "Verificar", "kind": "continue_running"},
        },
        "previous_plan": [{"id": "verify", "action": "Verificar", "status": "running"}],
    }
    decision = _task_controller_decision(active_task, type("Brain", (), {"plan_steps": []})(), "continúa")
    assert decision["action"] == "resume"
    assert decision["step_id"] == "verify"
    assert decision["trust"] == "continuity_only_not_evidence"
