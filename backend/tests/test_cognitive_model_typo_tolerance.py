from app.core.cognitive_model import CognitiveModel


def test_hoka_is_routed_as_greeting():
    state = CognitiveModel().process("hoka")
    assert state.intention["intent"] == "greeting"
    assert state.intention["domain"] == "general"
    assert state.plan["needs_evidence"] is False


def test_weather_typo_routes_to_weather_without_rewriting_user_message():
    model = CognitiveModel()
    state = model.process("como esta el tienpo hoy")
    assert state.intention["domain"] == "weather"
    assert state.plan["needs_evidence"] is True


def test_contiua_is_recognized_as_followup():
    model = CognitiveModel()
    state = model.process("contiua", {"domain": "trading"})
    assert state.intention["domain"] == "trading"


def test_original_message_is_preserved_for_generation():
    model = CognitiveModel()
    state = model.process("hoka")
    assert state.context["_cognitive_message"] == "hoka"


def test_weather_location_followup_keeps_weather_domain():
    model = CognitiveModel()
    first = model.process("que clima hay en Cuba")
    state = model.process("y en braisl esteio porto alegre?", {"last_user_request": "que clima hay en Cuba", "last_assistant_answer": "Clima en Cuba"})
    assert first.intention["domain"] == "weather"
    assert state.intention["domain"] == "weather"
    assert "esteio" in state.intention["entities"]["locations"]
    assert "porto alegre" in state.intention["entities"]["locations"]
    assert state.plan["needs_evidence"] is True
