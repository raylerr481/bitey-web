from app.core.artifact_pipeline import build_artifact, validate_artifact


def test_supported_artifact_is_validated_before_delivery():
    artifact = build_artifact(
        name="Plan — Documento",
        artifact_type="document",
        content={"format": "markdown", "content": "contenido"},
        metadata={"owner": "bitey_ia"},
    )
    assert artifact is not None
    assert artifact["status"] == "ready"
    assert artifact["metadata"]["validation"]["valid"] is True
    assert artifact["metadata"]["lifecycle"] == ["create", "validate", "evaluate", "deliver"]


def test_empty_artifact_is_rejected():
    result = validate_artifact("document", {"content": "   "})
    assert result["valid"] is False
    assert "empty_content" in result["errors"]


def test_unknown_artifact_type_is_rejected():
    result = validate_artifact("proprietary_format", "x")
    assert result["valid"] is False
    assert "unsupported_artifact_type" in result["errors"]
