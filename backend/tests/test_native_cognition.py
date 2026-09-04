from app.core.bitey_brain import BiteyBrain
from app.core.native_cognition import BiteyNativeCognitiveModel


def test_native_model_routes_research_without_external_model():
    model = BiteyNativeCognitiveModel()
    result = model.analyze("investiga y verifica las fuentes actuales sobre Python")
    assert result.research_required is True
    assert "native_perception" in result.capabilities
    assert result.confidence > 0


def test_native_model_detects_risk_signal():
    model = BiteyNativeCognitiveModel()
    result = model.analyze("ejecuta una orden con dinero real")
    assert result.signals["risk_gate"] > 0.5


def test_brain_uses_native_cognition_as_control_layer():
    brain = BiteyBrain()
    state = brain.think("diseña una arquitectura y verifica las fuentes")
    assert state.native_cognition["dominant_domain"] == "general"
    assert state.evidence_required is True
    assert brain.status()["native_cognitive_model"]["provider_independent"] is True
