"""Free-first artifact format contracts for Bitey IA Workspace.

The runtime keeps the canonical artifact content in a portable representation
and exposes conversion metadata for real file writers. Actual binary creation
can be delegated to the corresponding local worker without changing cognition.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ArtifactFormat:
    artifact_type: str
    extension: str
    mime_type: str
    editable: bool
    writer: str


FORMATS: dict[str, ArtifactFormat] = {
    "document": ArtifactFormat("document", ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", True, "python-docx"),
    "presentation": ArtifactFormat("presentation", ".pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", True, "python-pptx"),
    "spreadsheet": ArtifactFormat("spreadsheet", ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True, "openpyxl"),
    "code": ArtifactFormat("code", ".md", "text/markdown", True, "native-text"),
    "pdf": ArtifactFormat("pdf", ".pdf", "application/pdf", False, "reportlab"),
}


def describe_formats() -> list[dict[str, Any]]:
    return [vars(item) for item in FORMATS.values()]


def resolve_format(artifact_type: str) -> ArtifactFormat | None:
    return FORMATS.get(artifact_type)
