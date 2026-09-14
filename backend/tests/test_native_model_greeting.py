from app.core.cognitive_architecture import BiteyCognitiveArchitecture
from app.core.native_model import NativeReasoningModel


def test_greeting_is_conversational_and_does_not_use_evidence_fallback():
    model = NativeReasoningModel()
    frame = BiteyCognitiveArchitecture().run("hola", {})["frame"]

    answer = model._direct_general_answer("hola", frame)

    assert frame["intent"] == "greeting"
    assert frame["domain"] == "general"
    assert frame["evidence_required"] is False
    assert "evidencia verificada" not in answer.lower()
    assert "confianza cognitiva" not in answer.lower()
    assert "hola" in answer.lower()
