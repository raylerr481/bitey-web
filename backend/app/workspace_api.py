from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException

from .core.artifact_pipeline import build_artifact, validate_artifact
from .core.component_policy import component_manifest, validate_core_components
from .core.multistep_runtime import MultiStepResearchRuntime
from .core.task_contract_store import contract_from_task, persist_contract, sync_contract_from_execution
from .core.workspace_execution import WorkspaceExecutionService

router = APIRouter(prefix="/api/v1", tags=["Bitey Workspace"])

_MEMORY: dict[str, dict[str, Any]] = {}
_TASKS: dict[str, dict[str, Any]] = {}
_ARTIFACTS: dict[str, dict[str, Any]] = {}
_RUNTIME = MultiStepResearchRuntime(max_steps=4, max_sources_per_step=5)
_EXECUTOR = WorkspaceExecutionService()

TERMINAL_STATUSES = {"completed", "needs_review", "failed"}


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
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=representation"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.request(method, f"{url}/rest/v1/{table}", headers=headers, **kwargs)
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Supabase {table} error")
        return r.json() if r.content else []


async def _rpc(function: str, payload: dict[str, Any]) -> Any:
    cfg = _supabase()
    if not cfg:
        return None
    url, key = cfg
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{url}/rest/v1/rpc/{function}", headers=headers, json=payload)
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Supabase rpc {function} error")
        return r.json() if r.content else None


async def _workspace_exists(workspace_id: str) -> bool:
    rows = await _db("GET", "workspaces", params={"select": "id", "id": f"eq.{workspace_id}", "limit": "1"})
    return bool(rows) or workspace_id in _MEMORY


async def _get_task(workspace_id: str, task_id: str) -> dict[str, Any] | None:
    task = _TASKS.get(task_id)
    if task and task.get("workspace_id") == workspace_id:
        return task
    rows = await _db("GET", "workspace_tasks", params={"select": "*", "id": f"eq.{task_id}", "workspace_id": f"eq.{workspace_id}", "limit": "1"})
    if not rows:
        return None
    task = rows[0]
    # Hydrate the in-process cache from the durable task record. The contract
    # lives inside JSON metadata, so no schema migration is required.
    try:
        contract = contract_from_task(task)
        persist_contract(task, contract)
    except ValueError:
        # Keep the persisted row readable even if an older/invalid contract
        # exists; execution will surface a bounded failure instead of guessing.
        pass
    _TASKS[task_id] = task
    return task


async def _save_task(task: dict[str, Any]) -> dict[str, Any]:
    _TASKS[task["id"]] = task
    rows = await _db("PATCH", "workspace_tasks", json=task, params={"id": f"eq.{task['id']}"})
    return rows[0] if rows else task


async def _persist_contract(task: dict[str, Any], contract: Any) -> dict[str, Any]:
    persist_contract(task, contract)
    task["updated_at"] = _now()
    if _supabase():
        rows = await _db("PATCH", "workspace_tasks", json={"metadata": task["metadata"], "updated_at": task["updated_at"]}, params={"id": f"eq.{task['id']}", "workspace_id": f"eq.{task['workspace_id']}"})
        if rows:
            task = rows[0]
            _TASKS[task["id"]] = task
    else:
        _TASKS[task["id"]] = task
    return task


@router.get("/architecture/components")
async def architecture_components() -> dict[str, Any]:
    validate_core_components()
    manifest = component_manifest()
    return {"policy": "zero_cost", "decision_owner": "bitey_ia", "paid_fallback": False, "vendor_lock_in": False, "all_allowed": all(item["allowed"] for item in manifest), "components": manifest}


@router.get("/workspace/catalog")
async def workspace_catalog() -> dict[str, Any]:
    return {"product": "Bitey IA Workspace", "principle": "Bitey piensa y decide; modelos y herramientas son workers", "capabilities": [{"id": "chat", "label": "Chat", "kind": "conversation"}, {"id": "deep_research", "label": "Investigación profunda", "kind": "research"}, {"id": "browser_research", "label": "Investigación web", "kind": "research"}, {"id": "documents", "label": "Documentos", "kind": "artifact"}, {"id": "slides", "label": "Presentaciones", "kind": "artifact"}, {"id": "spreadsheets", "label": "Hojas de cálculo", "kind": "artifact"}, {"id": "code", "label": "Código", "kind": "artifact"}, {"id": "files", "label": "Archivos", "kind": "context"}, {"id": "projects", "label": "Proyectos", "kind": "workspace"}, {"id": "agents", "label": "Agentes", "kind": "orchestration"}], "execution": {"deterministic_first": True, "free_only": True, "paid_fallback": False, "human_authorization_for_side_effects": True}, "storage": {"canonical": "supabase", "local_fallback": True}, "research_runtime": _RUNTIME.status()}


@router.post("/workspaces")
async def create_workspace(payload: dict[str, Any]) -> dict[str, Any]:
    row = {"id": str(uuid4()), "name": str(payload.get("name") or "Nuevo espacio"), "description": str(payload.get("description") or ""), "mode": str(payload.get("mode") or "general"), "metadata": payload.get("metadata") or {}, "created_at": _now(), "updated_at": _now()}
    rows = await _db("POST", "workspaces", json=row)
    if rows: row = rows[0]
    _MEMORY[row["id"]] = row
    return row


@router.get("/workspaces")
async def list_workspaces() -> dict[str, Any]:
    rows = await _db("GET", "workspaces", params={"select": "*", "order": "updated_at.desc"})
    if not rows: rows = list(_MEMORY.values())
    return {"workspaces": rows}


@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str) -> dict[str, Any]:
    rows = await _db("GET", "workspaces", params={"select": "*", "id": f"eq.{workspace_id}", "limit": "1"})
    workspace = rows[0] if rows else _MEMORY.get(workspace_id)
    if not workspace: raise HTTPException(status_code=404, detail="workspace_not_found")
    tasks = await _db("GET", "workspace_tasks", params={"select": "*", "workspace_id": f"eq.{workspace_id}", "order": "created_at.desc"})
    if not tasks: tasks = [x for x in _TASKS.values() if x["workspace_id"] == workspace_id]
    for task in tasks:
        try:
            persist_contract(task, contract_from_task(task))
        except ValueError:
            pass
    artifacts = await _db("GET", "workspace_artifacts", params={"select": "*", "workspace_id": f"eq.{workspace_id}", "order": "created_at.desc"})
    if not artifacts: artifacts = [x for x in _ARTIFACTS.values() if x["workspace_id"] == workspace_id]
    return {"workspace": workspace, "tasks": tasks, "artifacts": artifacts}


@router.post("/workspaces/{workspace_id}/tasks")
async def create_task(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not await _workspace_exists(workspace_id): raise HTTPException(status_code=404, detail="workspace_not_found")
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt: raise HTTPException(status_code=422, detail="prompt_required")
    metadata = dict(payload.get("metadata") or {})
    max_retries = int(metadata.get("max_retries", 2))
    if max_retries < 0: raise HTTPException(status_code=422, detail="invalid_retry_budget")
    task_id = str(uuid4())
    contract = __import__("app.core.task_contract", fromlist=["TaskContract"]).TaskContract(task_id=task_id, prompt=prompt, capability=str(payload.get("capability") or "chat"), budget={"paid_inference": False, "max_retries": max_retries})
    persist_contract({"metadata": metadata}, contract)
    metadata = {**metadata, "task_contract": metadata["task_contract"], "retry_count": 0}
    task = {"id": task_id, "workspace_id": workspace_id, "title": str(payload.get("title") or prompt[:80] or "Nueva tarea"), "prompt": prompt, "capability": str(payload.get("capability") or "chat"), "status": "queued", "metadata": metadata, "created_at": _now(), "updated_at": _now()}
    rows = await _db("POST", "workspace_tasks", json=task)
    if rows: task = rows[0]
    _TASKS[task["id"]] = task
    return task


async def _execute_task(workspace_id: str, task_id: str, task: dict[str, Any]) -> dict[str, Any]:
    try:
        contract = contract_from_task(task)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    execution_token = str(uuid4())
    if _supabase():
        claimed = await _rpc("claim_workspace_task", {"p_workspace_id": workspace_id, "p_task_id": task_id, "p_execution_token": execution_token})
        if claimed is not True:
            latest = await _get_task(workspace_id, task_id)
            if latest and str(latest.get("status")) in TERMINAL_STATUSES: return latest
            raise HTTPException(status_code=409, detail="task_already_running")
        task.update({"status": "running", "execution_token": execution_token, "started_at": task.get("started_at") or _now(), "updated_at": _now()})
        _TASKS[task_id] = task
    else:
        if str(task.get("status") or "queued") != "queued":
            if str(task.get("status")) in TERMINAL_STATUSES: return task
            raise HTTPException(status_code=409, detail="task_already_running")
        task.update({"status": "running", "execution_token": execution_token, "started_at": task.get("started_at") or _now(), "updated_at": _now()})
        await _save_task(task)

    try:
        contract.transition("planning")
        await _persist_contract(task, contract)
        execution = await _EXECUTOR.execute(prompt=str(task.get("prompt") or ""), capability=str(task.get("capability") or "chat"), context={"workspace_id": workspace_id, "task_id": task_id, "metadata": task.get("metadata") or {}})
        contract = sync_contract_from_execution(task, execution)
        # Runtime contract is authoritative for cognitive planning; retry
        # count remains persisted by the workspace API.
        contract.retry_count = int((task.get("metadata") or {}).get("retry_count") or 0)
        contract.validate()
        await _persist_contract(task, contract)

        artifact_data = execution.get("artifact")
        if artifact_data:
            artifact = {"id": str(uuid4()), "workspace_id": workspace_id, "task_id": task_id, **artifact_data, "created_at": _now(), "updated_at": _now()}
            rows = await _db("POST", "workspace_artifacts", json=artifact)
            if rows: artifact = rows[0]
            _ARTIFACTS[artifact["id"]] = artifact
            execution["artifact"] = artifact
        status = str(execution.get("status") or "needs_review")
        if status not in TERMINAL_STATUSES: status = "needs_review"
        if status == "completed": contract.transition("completed")
        elif status == "needs_review": contract.transition("needs_review", reason="runtime_requires_review")
        else: contract.transition("failed", reason="runtime_failed")
        persist_contract(task, contract)
        task.update({"status": status, "updated_at": _now(), "completed_at": _now(), "result": execution})
        task["metadata"]["task_contract"] = {"version": 1, **contract.to_dict()}
        if _supabase():
            finished = await _rpc("finish_workspace_task", {"p_workspace_id": workspace_id, "p_task_id": task_id, "p_execution_token": execution_token, "p_status": status})
            if finished is not True:
                latest = await _get_task(workspace_id, task_id); return latest or task
            rows = await _db("PATCH", "workspace_tasks", json={"result": execution, "metadata": task["metadata"], "updated_at": task["updated_at"]}, params={"id": f"eq.{task_id}", "workspace_id": f"eq.{workspace_id}", "execution_token": f"eq.{execution_token}"})
            if rows: task = rows[0]
            _TASKS[task_id] = task
        else: await _save_task(task)
        return task
    except HTTPException: raise
    except Exception as exc:
        try:
            contract.transition("failed", reason=type(exc).__name__)
            persist_contract(task, contract)
        except ValueError:
            pass
        task.update({"status": "failed", "updated_at": _now(), "completed_at": _now(), "result": {"error": type(exc).__name__}})
        if _supabase():
            await _rpc("finish_workspace_task", {"p_workspace_id": workspace_id, "p_task_id": task_id, "p_execution_token": execution_token, "p_status": "failed"})
            await _db("PATCH", "workspace_tasks", json={"result": task["result"], "metadata": task.get("metadata") or {}, "updated_at": task["updated_at"]}, params={"id": f"eq.{task_id}", "workspace_id": f"eq.{workspace_id}", "execution_token": f"eq.{execution_token}"})
        else: await _save_task(task)
        raise HTTPException(status_code=502, detail="workspace_task_execution_failed")


@router.post("/workspaces/{workspace_id}/tasks/{task_id}/run")
async def run_task(workspace_id: str, task_id: str) -> dict[str, Any]:
    task = await _get_task(workspace_id, task_id)
    if not task: raise HTTPException(status_code=404, detail="task_not_found")
    status = str(task.get("status") or "queued")
    if status in TERMINAL_STATUSES: return task
    return await _execute_task(workspace_id, task_id, task)


@router.post("/workspaces/{workspace_id}/tasks/{task_id}/retry")
async def retry_task(workspace_id: str, task_id: str) -> dict[str, Any]:
    task = await _get_task(workspace_id, task_id)
    if not task: raise HTTPException(status_code=404, detail="task_not_found")
    status = str(task.get("status") or "queued")
    if status == "running": raise HTTPException(status_code=409, detail="task_already_running")
    if status not in {"failed", "needs_review"}: raise HTTPException(status_code=409, detail="task_not_retryable")
    try:
        contract = contract_from_task(task)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    next_retry = contract.retry_count + 1
    max_retries = int(contract.budget.get("max_retries", 2))
    if next_retry > max_retries:
        raise HTTPException(status_code=409, detail="retry_budget_exhausted")
    contract.retry_count = next_retry
    contract.transition("pending", reason="manual_retry")
    metadata = dict(task.get("metadata") or {})
    metadata["retry_count"] = next_retry
    task.update({"status": "queued", "result": None, "metadata": metadata, "execution_token": None, "started_at": None, "completed_at": None, "updated_at": _now()})
    persist_contract(task, contract)
    await _save_task(task)
    return await _execute_task(workspace_id, task_id, task)


@router.get("/workspaces/{workspace_id}/tasks/{task_id}")
async def get_task(workspace_id: str, task_id: str) -> dict[str, Any]:
    task = await _get_task(workspace_id, task_id)
    if not task: raise HTTPException(status_code=404, detail="task_not_found")
    return task


@router.get("/workspace/runtime/status")
async def runtime_status() -> dict[str, Any]:
    return _RUNTIME.status()


@router.post("/workspaces/{workspace_id}/artifacts")
async def create_artifact(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not await _workspace_exists(workspace_id): raise HTTPException(status_code=404, detail="workspace_not_found")
    name = str(payload.get("name") or "Nuevo artefacto").strip()
    artifact_type = str(payload.get("artifact_type") or "document").strip().lower()
    content = payload.get("content")
    try:
        validation = validate_artifact(artifact_type, content)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_artifact", "message": str(exc)}) from exc
    artifact = build_artifact(name=name, artifact_type=artifact_type, content=content, metadata={**(payload.get("metadata") or {}), "creation_mode": "workspace_api"})
    artifact.update({"id": str(uuid4()), "workspace_id": workspace_id, "status": "draft", "validation": validation, "created_at": _now(), "updated_at": _now()})
    rows = await _db("POST", "workspace_artifacts", json=artifact)
    if rows: artifact = rows[0]
    _ARTIFACTS[artifact["id"]] = artifact
    return artifact


@router.get("/workspaces/{workspace_id}/artifacts")
async def list_artifacts(workspace_id: str) -> dict[str, Any]:
    if not await _workspace_exists(workspace_id): raise HTTPException(status_code=404, detail="workspace_not_found")
    rows = await _db("GET", "workspace_artifacts", params={"select": "*", "workspace_id": f"eq.{workspace_id}", "order": "updated_at.desc"})
    if not rows: rows = [x for x in _ARTIFACTS.values() if x["workspace_id"] == workspace_id]
    return {"artifacts": rows}
