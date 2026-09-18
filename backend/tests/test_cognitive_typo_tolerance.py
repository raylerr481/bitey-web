from app.core.cognitive_architecture import BiteyCognitiveArchitecture


def test_typo_hoka_is_greeting():
    frame = BiteyCognitiveArchitecture().perceive("hoka", {})
    assert frame.intent == "greeting"
    assert frame.domain == "general"
    assert frame.confidence >= 0.90


def test_hola_remains_greeting():
    frame = BiteyCognitiveArchitecture().perceive("hola", {})
    assert frame.intent == "greeting"
    assert frame.domain == "general"


def test_original_user_text_is_preserved():
    frame = BiteyCognitiveArchitecture().perceive("hoka, como estas?", {})
    assert frame.input_text == "hoka, como estas?"
    assert frame.intent == "greeting"
