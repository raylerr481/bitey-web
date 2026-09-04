import pytest

from app.core.artifact_engine import ArtifactEngine


@pytest.mark.parametrize(
    ("artifact_type", "artifact_format"),
    [("document", "markdown"), ("presentation", "slide-ready"), ("spreadsheet", "table-ready"), ("code", "source-ready")],
)
def test_artifact_engine_builds_valid_contracts(artifact_type, artifact_format):
    artifact = ArtifactEngine().build(
        prompt="Crea un recurso de prueba",
        answer="Contenido suficientemente largo para validar el contrato del artefacto.",
        artifact_type=artifact_type,
        metadata={"authorization": "bitey_brain_bounded_gate"},
    )

    assert artifact.status == "ready"
    assert artifact.artifact_type == artifact_type
    assert artifact.content["format"] == artifact_format
    assert artifact.content["content"]


def test_artifact_engine_rejects_missing_authorization():
    with pytest.raises(ValueError, match="artifact_authorization_missing"):
        ArtifactEngine().build(
            prompt="Documento",
            answer="Contenido suficientemente largo para validar el contrato.",
            artifact_type="document",
            metadata={},
        )


def test_artifact_engine_rejects_unknown_type():
    with pytest.raises(ValueError, match="unsupported_artifact_type"):
        ArtifactEngine().build(
            prompt="Recurso",
            answer="Contenido suficientemente largo para validar el contrato.",
            artifact_type="unknown",
            metadata={"authorization": "bitey_brain_bounded_gate"},
        )
