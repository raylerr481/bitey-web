"""HTTP API for Bitey IA unified workspace tasks and artifacts."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from ..core.capability_registry import CapabilityRegistry
from ..core.workspace_runtime import WorkspaceRuntime
from ..core.task_artifacts import TaskArtifactRuntime

router = APIRouter(prefix="/api/v1/workspace", tags=["workspace"])
registry = CapabilityRegistry()
runtime = WorkspaceRuntime(registry)
tasks = TaskArtifactRuntime()


def _plan(request: str, mode: str = "general", domain: str = "general", metadata: dict[str, Any] | None = None):
    plan = runtime.plan(request, mode=mode, domain=domain, metadata=metadata)
    tasks._tasks[plan.task.task_id] = plan.task
    return plan


@router.get("/capabilities")
async def workspace_capabilities() -> dict[str, Any]:
    return {"capabilities": [item.as_dict() for item in registry.all()], "free_only": True}


@router.post("/tasks")
async def create_workspace_task(payload: dict[str, Any]) -> dict[str, Any]:
    request = str(payload.get("request") or payload.get("message") or "").strip()
    if not request:
        raise HTTPException(status_code=400, detail="request is required")
    plan = _plan(request, mode=str(payload.get("mode") or "general"), domain=str(payload.get("domain") or "general"), metadata=payload.get("metadata") or {})
    return {"task": plan.task.as_dict(), "capabilities": plan.capabilities}


@router.get("/tasks")
async def list_workspace_tasks() -> dict[str, Any]:
    return {"tasks": [task.as_dict() for task in reversed(tasks.list())]}


@router.get("/tasks/{task_id}")
async def get_workspace_task(task_id: str) -> dict[str, Any]:
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return {"task": task.as_dict()}


@router.get("/tasks/{task_id}/artifacts")
async def get_workspace_artifacts(task_id: str) -> dict[str, Any]:
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return {"task_id": task_id, "artifacts": [item.as_dict() for item in task.artifacts]}
