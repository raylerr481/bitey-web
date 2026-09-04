"""Deterministic artifact contracts for Bitey IA Workspace."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Artifact:
    name: str
    artifact_type: str
    status: str
    content: dict[str, Any]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArtifactEngine:
    """Build and validate in-app artifacts after Bitey's authorization gate.

    This layer deliberately does not invoke a model and does not authorize
    execution. It converts generated text into a stable product contract.
    """

    FORMATS = {
        "document": "markdown",
        "presentation": "slide-ready",
        "spreadsheet": "table-ready",
        "code": "source-ready",
    }

    def build(
        self,
        *,
        prompt: str,
        answer: str,
        artifact_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        if artifact_type not in self.FORMATS:
            raise ValueError(f"unsupported_artifact_type:{artifact_type}")
        text = (answer or "").strip()
        if not text:
            raise ValueError("artifact_content_empty")
        name = self._name(prompt, artifact_type)
        artifact = Artifact(
            name=name,
            artifact_type=artifact_type,
            status="ready",
            content={"format": self.FORMATS[artifact_type], "content": text},
            metadata=dict(metadata or {}),
        )
        self.validate(artifact)
        return artifact

    @staticmethod
    def validate(artifact: Artifact) -> None:
        if not artifact.name.strip():
            raise ValueError("artifact_name_empty")
        if artifact.status != "ready":
            raise ValueError("artifact_not_ready")
        if not artifact.content.get("format") or not artifact.content.get("content"):
            raise ValueError("artifact_content_invalid")
        if artifact.metadata.get("authorization") != "bitey_brain_bounded_gate":
            raise ValueError("artifact_authorization_missing")

    @staticmethod
    def _name(prompt: str, artifact_type: str) -> str:
        title = " ".join(prompt.strip().split())[:70] or "Nuevo artefacto"
        suffix = {
            "document": "Documento",
            "presentation": "Presentación",
            "spreadsheet": "Hoja de cálculo",
            "code": "Código",
        }[artifact_type]
        return f"{title} — {suffix}"
