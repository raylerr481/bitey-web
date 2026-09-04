"""Unified AI workspace planning for Bitey IA.

Translates one user request into a bounded execution plan composed of
capabilities and artifacts. It does not call models or execute side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .capability_registry import CapabilityRegistry
from .task_artifacts import ArtifactContract, WorkspaceTask


@dataclass
class WorkspacePlan:
    task: WorkspaceTask
    capabilities: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"task": self.task.as_dict(), "capabilities": self.capabilities}


class WorkspaceRuntime:
    """Build bounded multi-output plans for the Bitey AI workspace."""

    OUTPUT_ALIASES = {
        "report": "documents", "document": "documents", "doc": "documents", "informe": "documents",
        "presentacion": "slides", "presentación": "slides", "ppt": "slides", "powerpoint": "slides",
        "excel": "sheets", "spreadsheet": "sheets", "hoja": "sheets",
        "imagen": "images", "image": "images", "website": "websites", "app": "websites",
        "codigo": "developer", "código": "developer", "video": "video", "podcast": "audio",
    }

    def __init__(self, registry: CapabilityRegistry | None = None, *, max_capabilities: int = 6, max_artifacts: int = 8) -> None:
        self.registry = registry or CapabilityRegistry()
        self.max_capabilities = max(1, max_capabilities)
        self.max_artifacts = max(1, max_artifacts)

    def plan(self, request: str, *, mode: str = "general", domain: str = "general", metadata: dict[str, Any] | None = None) -> WorkspacePlan:
        task = WorkspaceTask(task_id=str(uuid4()), request=request.strip(), capability="general", metadata=dict(metadata or {}))
        resolved = self.registry.resolve(mode=mode, domain=domain)
        selected = [item.id for item in resolved]
        task.capability = selected[0] if selected else "general"
        task.set_state("planning", 10)
        task.add_step("classify_request", "completed")
        task.add_step("select_capabilities", "completed", capabilities=selected)
        for capability in self._infer_output_capabilities(request):
            if capability not in selected and len(selected) < self.max_capabilities:
                selected.append(capability)
        for capability in selected[: self.max_artifacts]:
            task.add_artifact(ArtifactContract(
                artifact_id=str(uuid4()), kind=capability, title=self._artifact_title(capability),
                metadata={"planned_by": "bitey_brain", "capability": capability},
            ))
        task.set_state("queued", 15)
        return WorkspacePlan(task=task, capabilities=selected[: self.max_capabilities])

    def _infer_output_capabilities(self, text: str) -> list[str]:
        low = text.lower()
        found: list[str] = []
        for alias, capability in self.OUTPUT_ALIASES.items():
            if alias in low and capability not in found:
                found.append(capability)
        return found

    @staticmethod
    def _artifact_title(capability: str) -> str:
        titles = {
            "documents": "Documento / informe", "slides": "Presentación", "sheets": "Hoja de cálculo",
            "images": "Recurso visual", "websites": "Sitio / aplicación", "developer": "Entrega de código",
            "video": "Vídeo", "audio": "Audio / podcast", "research": "Investigación y fuentes",
            "markets": "Análisis de mercados", "general": "Respuesta",
        }
        return titles.get(capability, capability.title())
