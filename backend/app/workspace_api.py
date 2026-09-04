from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException

from .core.bitey_brain import BiteyBrain
from .core.multistep_runtime import MultiStepResearchRuntime
from .core.workspace_execution import WorkspaceExecutionService
from .core.workspace_orchestrator import WorkspaceOrchestrator

router = APIRouter(prefix="/api/v1", tags=["Bitey Workspace"])

_MEMORY: dict[str, dict[str, Any]] = {}
_TASKS: dict[str, dict[str, Any]] = {}
_ARTIFACTS: dict[str, dict[str, Any]] = {}
_RUNTIME = MultiStepResearchRuntime(max_steps=4, max_sources_per_step=5)
_EXECUTOR = WorkspaceExecutionService()
_ORCHESTRATOR = WorkspaceOrchestrator()
_BRAIN = BiteyBrain()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _supabase() -> tuple[str, str] | None:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    return (url, key) if url and key else None


async def _db(method: str, table: str, **kwargs: Any) -> list[dict[str, Any]]:
    cfg = _supabase()
    if not cfg:
        return []
    url, key = cfg
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.request(method, f"{url}/rest/v1/{table}", headers=headers, **kwargs)
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Supabase {table} error")
        return response.json() if response.content else []


async def _workspace_or_404(workspace_id: str) -> dict[str, Any]:
    rows = await _db("GET", "workspaces", params={"select": "*", "id": f"eq.{workspace_id}", "limit": "1"})
    workspace = rows[0] if rows else _MEMORY.get(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return workspace


async def _save_task(task: dict[str, Any]) -> dict[str, Any]:
    _TASKS[task["id"]] = task
    await _db("PATCH", "workspace_tasks", json=task, params={"id": f"eq.{task['id']}"})
    return task


async def _workspace_memory(workspace_id: str, limit: int = 12) -> list[dict[str, Any]]:
    rows = await _db(
        "GET",
        "workspace_memory",
        params={
            "select": "id,memory_type,memory_key,content,metadata,importance,created_at,updated_at",
            "workspace_id": f"eq.{workspace_id}",
            "order": "importance.desc,updated_at.desc",
            "limit": str(max(1, min(limit, 50))),
        },
    )
    if rows:
        return rows
    return [item for item in _MEMORY.values() if item.get("workspace_id") == workspace_id][:limit]


async def _save_memory(
    workspace_id: str,
    content: str,
    memory_type: str = "execution",
    memory_key: str | None = None,
    metadata: dict[str, Any] | None = None,
    importance: float = 0.6,
) -> dict[str, Any]:
    memory = {
        "id": str(uuid4()),
        "workspace_id": workspace_id,
        "memory_type": memory_type,
        "memory_key": memory_key,
        "content": content,
        "metadata": metadata or {},
        "importance": max(0.0, min(float(importance), 1.0)),
        "created_at": _now(),
        "updated_at": _now(),
    }
    rows = await _db("POST", "workspace_memory", json=memory)
    if rows:
        memory = rows[0]
    _MEMORY[memory["id"]] = memory
    return memory


async def _persist_artifact(workspace_id: str, task_id: str, artifact_data: dict[str, Any]) -> dict[str, Any]:
    artifact = {
        "id": str(uuid4()),
        "workspace_id": workspace_id,
        "task_id": task_id,
        **artifact_data,
        "created_at": _now(),
        "updated_at": _now(),
    }
    rows = await _db("POST", "workspace_artifacts", json=artifact)
    if rows:
        artifact = rows[0]
    _ARTIFACTS[artifact["id"]] = artifact
    return artifact


async def _persist_execution_artifacts(workspace_id: str, task_id: str, execution: dict[str, Any]) -> dict[str, Any]:
    persisted: list[dict[str, Any]] = []
    deliverables = execution.get("deliverables") or []
    for item in deliverables:
        result = item.get("result") or {}
        artifact_data = result.get("artifact")
        if artifact_data:
            artifact = await _persist_artifact(workspace_id, task_id, artifact_data)
            item["result"]["artifact"] = artifact
            persisted.append(artifact)

    # Backward compatibility for non-orchestrated tasks and older callers.
    if not persisted and execution.get("artifact"):
        artifact = await _persist_artifact(workspace_id, task_id, execution["artifact"])
        execution["artifact"] = artifact
        persisted.append(artifact)

    execution["artifacts"] = persisted
    return execution


@router.get("/workspace/catalog")
async def workspace_catalog() -> dict[str, Any]:
    return {
        "product": "Bitey IA Workspace",
        "principle": "Bitey piensa y decide; modelos y herramientas son workers",
        "capabilities": [
            {"id": "chat", "label": "Chat", "kind": "conversation"},
            {"id": "deep_research", "label": "Investigación profunda", "kind": "research"},
            {"id": "browser_research", "label": "Investigación web", "kind": "research"},
            {"id": "documents", "label": "Documentos", "kind": "artifact"},
            {"id": "slides", "label": "Presentaciones", "kind": "artifact"},
            {"id": "spreadsheets", "label": "Hojas de cálculo", "kind": "artifact"},
            {"id": "code", "label": "Código", "kind": "artifact"},
            {"id": "files", "label": "Archivos", "kind": "context"},
            {"id": "projects", "label": "Proyectos", "kind": "workspace"},
            {"id": "agents", "label": "Agentes", "kind": "orchestration"},
        ],
        "execution": {
            "deterministic_first": True,
            "free_only": True,
            "paid_fallback": False,
            "human_authorization_for_side_effects": True,
            "max_deliverables": WorkspaceOrchestrator.MAX_DELIVERABLES,
        },
        "storage": {"canonical": "supabase", "local_fallback": True},
        "research_runtime": _RUNTIME.status(),
    }


@router.post("/workspace/cognitive/inspect")
async def inspect_cognitive_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Return Bitey's deterministic plan before model inference."""
    prompt = str(payload.get("prompt") or "").strip()
    capability = str(payload.get("capability") or "chat")
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt_required")
    context = dict(payload.get("context") or {})
    workspace_id = str(context.get("workspace_id") or "").strip()
    memories: list[dict[str, Any]] = []
    if workspace_id:
        memories = await _workspace_memory(workspace_id)
        if memories:
            context["learned_cognitive_context"] = {"available": True, "items": memories}
    state = _BRAIN.think(prompt, context)
    research = capability in {"deep_research", "browser_research"} or state.evidence_required
    artifact_type = WorkspaceExecutionService.ARTIFACT_CAPABILITIES.get(capability)
    deliverables = [item.__dict__ for item in _ORCHESTRATOR.plan(prompt, capability=capability)]
    return {
        "owner": "bitey_ia",
        "authority": "bitey_brain",
        "model_invocation": False,
        "capability": capability,
        "route": "research" if research else ("artifact" if artifact_type else "conversation"),
        "artifact_type": artifact_type,
        "deliverables": deliverables,
        "brain": state.as_dict(),
        "research_runtime": _RUNTIME.status() if research else None,
        "memory_context": {"available": bool(workspace_id), "items": len(memories)},
        "side_effects": {"allowed": state.execution_allowed, "human_authorization_required": True},
    }


@router.post("/workspaces")
async def create_workspace(payload: dict[str, Any]) -> dict[str, Any]:
    row = {
        "id": str(uuid4()),
        "name": str(payload.get("name") or "Nuevo espacio"),
        "description": str(payload.get("description") or ""),
        "mode": str(payload.get("mode") or "general"),
        "metadata": payload.get("metadata") or {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    rows = await _db("POST", "workspaces", json=row)
    if rows:
        row = rows[0]
    _MEMORY[row["id"]] = row
    return row


@router.get("/workspaces")
async def list_workspaces() -> dict[str, Any]:
    rows = await _db("GET", "workspaces", params={"select": "*", "order": "updated_at.desc"})
    if not rows:
        rows = [item for item in _MEMORY.values() if "name" in item]
    return {"workspaces": rows}


@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str) -> dict[str, Any]:
    workspace = await _workspace_or_404(workspace_id)
    tasks = await _db("GET", "workspace_tasks", params={"select": "*", "workspace_id": f"eq.{workspace_id}", "order": "created_at.desc"})
    if not tasks:
        tasks = [item for item in _TASKS.values() if item["workspace_id"] == workspace_id]
    artifacts = await _db("GET", "workspace_artifacts", params={"select": "*", "workspace_id": f"eq.{workspace_id}", "order": "created_at.desc"})
    if not artifacts:
        artifacts = [item for item in _ARTIFACTS.values() if item["workspace_id"] == workspace_id]
    memory = await _workspace_memory(workspace_id)
    return {"workspace": workspace, "tasks": tasks, "artifacts": artifacts, "memory": memory}


@router.post("/workspaces/{workspace_id}/tasks")
async def create_task(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    await _workspace_or_404(workspace_id)
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt_required")
    task = {
        "id": str(uuid4()),
        "workspace_id": workspace_id,
        "title": str(payload.get("title") or "Nueva tarea"),
        "prompt": prompt,
        "capability": str(payload.get("capability") or "chat"),
        "status": "queued",
        "metadata": payload.get("metadata") or {},
        "result": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    rows = await _db("POST", "workspace_tasks", json=task)
    if rows:
        task = rows[0]
    _TASKS[task["id"]] = task
    return task


@router.post("/workspaces/{workspace_id}/tasks/{task_id}/run")
async def run_task(workspace_id: str, task_id: str) -> dict[str, Any]:
    await _workspace_or_404(workspace_id)
    task = _TASKS.get(task_id)
    if not task:
        rows = await _db("GET", "workspace_tasks", params={"select": "*", "id": f"eq.{task_id}", "workspace_id": f"eq.{workspace_id}", "limit": "1"})
        task = rows[0] if rows else None
    if not task or task.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="task_not_found")
    if task.get("status") == "completed":
        return task

    task.update({"status": "running", "updated_at": _now()})
    await _save_task(task)
    try:
        memories = await _workspace_memory(workspace_id)
        execution_context = {
            "workspace_id": workspace_id,
            "task_id": task_id,
            "metadata": task.get("metadata") or {},
        }
        if memories:
            execution_context["learned_cognitive_context"] = {"available": True, "items": memories}

        execution = await _ORCHESTRATOR.execute(
            prompt=str(task.get("prompt") or ""),
            capability=str(task.get("capability") or "chat"),
            context=execution_context,
        )
        execution = await _persist_execution_artifacts(workspace_id, task_id, execution)
        task.update({
            "status": execution.get("status", "needs_review"),
            "updated_at": _now(),
            "result": execution,
        })
        await _save_task(task)
        await _save_memory(
            workspace_id,
            content=str(task.get("prompt") or ""),
            memory_type="task_context",
            memory_key=f"task:{task_id}",
            metadata={
                "task_id": task_id,
                "capability": task.get("capability"),
                "status": task.get("status"),
                "cognitive_decision": execution.get("cognitive_decision"),
                "deliverable_count": execution.get("deliverable_count", 0),
                "artifact_count": len(execution.get("artifacts") or []),
                "execution_trace": execution.get("execution_trace", []),
            },
            importance=0.65,
        )
        return task
    except Exception as exc:
        task.update({"status": "failed", "updated_at": _now(), "result": {"error": type(exc).__name__}})
        await _save_task(task)
        raise HTTPException(status_code=502, detail="workspace_task_execution_failed")


@router.get("/workspaces/{workspace_id}/tasks/{task_id}")
async def get_task(workspace_id: str, task_id: str) -> dict[str, Any]:
    await _workspace_or_404(workspace_id)
    task = _TASKS.get(task_id)
    if not task:
        rows = await _db("GET", "workspace_tasks", params={"select": "*", "id": f"eq.{task_id}", "workspace_id": f"eq.{workspace_id}", "limit": "1"})
        task = rows[0] if rows else None
    if not task or task.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="task_not_found")
    return task


@router.get("/workspaces/{workspace_id}/memory")
async def list_memory(workspace_id: str) -> dict[str, Any]:
    await _workspace_or_404(workspace_id)
    return {"memory": await _workspace_memory(workspace_id, limit=50)}


@router.post("/workspaces/{workspace_id}/memory")
async def create_memory(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    await _workspace_or_404(workspace_id)
    content = str(payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="memory_content_required")
    return await _save_memory(
        workspace_id,
        content=content,
        memory_type=str(payload.get("memory_type") or "context"),
        memory_key=str(payload.get("memory_key") or "") or None,
        metadata=payload.get("metadata") or {},
        importance=float(payload.get("importance", 0.5)),
    )


@router.get("/workspace/runtime/status")
async def runtime_status() -> dict[str, Any]:
    return _RUNTIME.status()


@router.post("/workspaces/{workspace_id}/artifacts")
async def create_artifact(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    await _workspace_or_404(workspace_id)
    artifact = {
        "id": str(uuid4()),
        "workspace_id": workspace_id,
        "task_id": payload.get("task_id"),
        "name": str(payload.get("name") or "Nuevo artefacto"),
        "artifact_type": str(payload.get("artifact_type") or "document"),
        "status": "draft",
        "content": payload.get("content"),
        "metadata": payload.get("metadata") or {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    rows = await _db("POST", "workspace_artifacts", json=artifact)
    if rows:
        artifact = rows[0]
    _ARTIFACTS[artifact["id"]] = artifact
    return artifact


@router.get("/workspaces/{workspace_id}/artifacts")
async def list_artifacts(workspace_id: str) -> dict[str, Any]:
    await _workspace_or_404(workspace_id)
    rows = await _db("GET", "workspace_artifacts", params={"select": "*", "workspace_id": f"eq.{workspace_id}", "order": "updated_at.desc"})
    if not rows:
        rows = [item for item in _ARTIFACTS.values() if item["workspace_id"] == workspace_id]
    return {"artifacts": rows}


@router.get("/workspaces/{workspace_id}/artifacts/{artifact_id}")
async def get_artifact(workspace_id: str, artifact_id: str) -> dict[str, Any]:
    await _workspace_or_404(workspace_id)
    rows = await _db("GET", "workspace_artifacts", params={"select": "*", "id": f"eq.{artifact_id}", "workspace_id": f"eq.{workspace_id}", "limit": "1"})
    artifact = rows[0] if rows else _ARTIFACTS.get(artifact_id)
    if not artifact or artifact.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    return artifact
