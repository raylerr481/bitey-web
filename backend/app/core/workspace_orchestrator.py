"""Bounded orchestration for Bitey IA multi-deliverable workspace tasks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .workspace_execution import WorkspaceExecutionService


@dataclass(frozen=True)
class Deliverable:
    capability: str
    artifact_type: str
    reason: str


class WorkspaceOrchestrator:
    """Turn one user request into a small, explicit set of deliverables.

    Bitey remains the authority: this class only plans and coordinates bounded
    workers. It never grants side effects or bypasses the execution service.
    """

    MAX_DELIVERABLES = 4
    KEYWORDS = {
        "document": ("document", "docx", "informe", "report", "documento", "pdf"),
        "presentation": ("presentation", "slides", "ppt", "pptx", "presentación", "diapositivas"),
        "spreadsheet": ("spreadsheet", "excel", "xlsx", "csv", "hoja", "tabla", "datos"),
        "code": ("code", "codigo", "código", "programa", "script", "developer"),
    }

    def __init__(self, execution: WorkspaceExecutionService | None = None) -> None:
        self.execution = execution or WorkspaceExecutionService()

    def plan(self, prompt: str, requested_capability: str = "chat") -> list[Deliverable]:
        text = prompt.lower()
        found: list[Deliverable] = []
        for artifact_type, words in self.KEYWORDS.items():
            if any(word in text for word in words):
                capability = next((k for k, v in self.execution.ARTIFACT_CAPABILITIES.items() if v == artifact_type), artifact_type)
                found.append(Deliverable(capability, artifact_type, "requested_or_detected_from_prompt"))
        if not found and requested_capability in self.execution.ARTIFACT_CAPABILITIES:
            artifact_type = self.execution.ARTIFACT_CAPABILITIES[requested_capability]
            found.append(Deliverable(requested_capability, artifact_type, "explicit_capability"))
        return found[: self.MAX_DELIVERABLES]

    async def execute(self, *, prompt: str, capability: str = "chat", context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {})
        deliverables = self.plan(prompt, capability)
        if not deliverables:
            return await self.execution.execute(prompt=prompt, capability=capability, context=ctx)

        results: list[dict[str, Any]] = []
        for item in deliverables:
            result = await self.execution.execute(prompt=prompt, capability=item.capability, context={**ctx, "orchestration": {"artifact_type": item.artifact_type, "reason": item.reason}})
            results.append({"capability": item.capability, "artifact_type": item.artifact_type, "result": result})
            if result.get("status") not in {"completed", "needs_review"}:
                break

        accepted = sum(1 for item in results if item["result"].get("status") == "completed")
        return {
            "status": "completed" if accepted == len(results) and results else "needs_review",
            "orchestrated": True,
            "deliverable_count": len(deliverables),
            "completed_count": accepted,
            "deliverables": results,
            "execution_policy": {"max_deliverables": self.MAX_DELIVERABLES, "sequential": True, "side_effects": "delegated_to_workspace_execution_gate"},
        }
