"""Deterministic, dependency-free artifact lifecycle for Bitey Workspace."""
from __future__ import annotations

from typing import Any

SUPPORTED_TYPES = {"document", "presentation", "spreadsheet", "code"}


def validate_artifact(artifact_type: str, content: Any) -> dict[str, Any]:
    """Validate the minimum safe deliverable contract without a paid service."""
    errors: list[str] = []
    if artifact_type not in SUPPORTED_TYPES:
        errors.append("unsupported_artifact_type")
    if content is None or content == "":
        errors.append("empty_content")
    if isinstance(content, dict) and not str(content.get("content", "")).strip():
        errors.append("empty_content")
    return {"valid": not errors, "errors": errors, "stage": "validate"}


def build_artifact(*, name: str, artifact_type: str, content: Any, metadata: dict[str, Any]) -> dict[str, Any] | None:
    validation = validate_artifact(artifact_type, content)
    if not validation["valid"]:
        return None
    return {
        "name": name,
        "artifact_type": artifact_type,
        "status": "ready",
        "content": content,
        "metadata": {**metadata, "validation": validation, "lifecycle": ["create", "validate", "evaluate", "deliver"]},
    }
