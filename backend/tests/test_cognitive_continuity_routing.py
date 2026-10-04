from app.core.cognitive_model import CognitiveModel


def test_short_followup_inherits_weather_topic_from_structured_context():
    model = CognitiveModel()
    context = {
        "last_user_request": "¿Qué clima hay en Cuba?",
        "last_assistant_answer": "Debemos consultar el clima actual.",
        "conversation_context": {
            "topic": "weather",
            "entities": ["Cuba"],
            "continuation": True,
        },
    }
    state = model.process("¿Y mañana?", context, evidence_available=False)
    assert state.intention["domain"] == "weather"
    assert state.intention["intent_family"] == "weather"
    assert "Cuba" in (state.intention["entities"].get("locations") or [])


def test_current_request_can_override_previous_weather_topic():
    model = CognitiveModel()
    context = {
        "last_user_request": "¿Qué clima hay en Cuba?",
        "last_assistant_answer": "Consulta meteorológica.",
        "conversation_context": {"topic": "weather", "entities": ["Cuba"]},
    }
    state = model.process("Explícame Docker", context, evidence_available=False)
    assert state.intention["domain"] == "programming"
