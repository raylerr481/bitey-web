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
