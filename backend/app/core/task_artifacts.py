"""Task and artifact contracts for the Bitey unified AI workspace.

These contracts deliberately remain provider-agnostic: Bitey Brain owns task
planning and validation while models/tools are execution resources.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


TASK_STATES = {"queued", "planning", "running", "waiting", "completed", "failed", "cancelled"}
ARTIFACT_STATES = {"planned", "generating", "ready", "failed"}


@dataclass
class ArtifactContract:
    artifact_id: str
    kind: str
    title: str
    state: str = "planned"
    mime_type: str | None = None
    uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind,
            "title": self.title,
            "state": self.state,
            "mime_type": self.mime_type,
            "uri": self.uri,
            "metadata": self.metadata,
        }


@dataclass
class WorkspaceTask:
    task_id: str
    request: str
    capability: str = "general"
    state: str = "queued"
    progress: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    steps: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[ArtifactContract] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def set_state(self, state: str, progress: int | None = None) -> None:
        if state not in TASK_STATES:
            raise ValueError(f"Unsupported task state: {state}")
        self.state = state
        if progress is not None:
            self.progress = max(0, min(100, progress))
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def add_step(self, name: str, state: str = "queued", **metadata: Any) -> dict[str, Any]:
        step = {"name": name, "state": state, **metadata}
        self.steps.append(step)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return step

    def add_artifact(self, artifact: ArtifactContract) -> ArtifactContract:
        if artifact.state not in ARTIFACT_STATES:
            raise ValueError(f"Unsupported artifact state: {artifact.state}")
        self.artifacts.append(artifact)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return artifact

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "request": self.request,
            "capability": self.capability,
            "state": self.state,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": self.steps,
            "artifacts": [item.as_dict() for item in self.artifacts],
            "metadata": self.metadata,
        }


class TaskArtifactRuntime:
    """In-memory bounded task registry used until persistent workspace storage is wired."""

    def __init__(self, max_tasks: int = 100) -> None:
        self.max_tasks = max(1, max_tasks)
        self._tasks: dict[str, WorkspaceTask] = {}

    def create(self, task_id: str, request: str, capability: str = "general", **metadata: Any) -> WorkspaceTask:
        if len(self._tasks) >= self.max_tasks:
            oldest = next(iter(self._tasks))
            self._tasks.pop(oldest, None)
        task = WorkspaceTask(task_id=task_id, request=request, capability=capability, metadata=metadata)
        self._tasks[task_id] = task
        return task

    def get(self, task_id: str) -> WorkspaceTask | None:
        return self._tasks.get(task_id)

    def list(self) -> list[WorkspaceTask]:
        return list(self._tasks.values())
