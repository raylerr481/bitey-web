from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1", tags=["Skywork-style workspace"])

_MEMORY: dict[str, dict[str, Any]] = {}
_TASKS: dict[str, dict[str, Any]] = {}
_ARTIFACTS: dict[str, dict[str, Any]] = {}


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


@router.get("/workspace/catalog")
async def workspace_catalog() -> dict[str, Any]:
    return {
        "product": "Bitey IA Workspace",
        "compatibility": "skywork-style",
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
        "execution": {"deterministic_first": True, "free_only": True, "paid_fallback": False, "human_authorization_for_side_effects": True},
        "storage": {"canonical": "supabase", "local_fallback": True},
    }


@router.post("/workspaces")
async def create_workspace(payload: dict[str, Any]) -> dict[str, Any]:
    row = {"id": str(uuid4()), "name": str(payload.get("name") or "Nuevo espacio"), "description": str(payload.get("description") or ""), "mode": str(payload.get("mode") or "general"), "metadata": payload.get("metadata") or {}, "created_at": _now(), "updated_at": _now()}
    rows = await _db("POST", "workspaces", json=row)
    if rows:
        row = rows[0]
    _MEMORY[row["id"]] = row
    return row


@router.get("/workspaces")
async def list_workspaces() -> dict[str, Any]:
    rows = await _db("GET", "workspaces", params={"select": "*", "order": "updated_at.desc"})
    if not rows:
        rows = list(_MEMORY.values())
    return {"workspaces": rows}


@router.get("/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str) -> dict[str, Any]:
    rows = await _db("GET", "workspaces", params={"select": "*", "id": f"eq.{workspace_id}", "limit": "1"})
    workspace = rows[0] if rows else _MEMORY.get(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    tasks = await _db("GET", "workspace_tasks", params={"select": "*", "workspace_id": f"eq.{workspace_id}", "order": "created_at.desc"})
    if not tasks:
        tasks = [x for x in _TASKS.values() if x["workspace_id"] == workspace_id]
    artifacts = await _db("GET", "workspace_artifacts", params={"select": "*", "workspace_id": f"eq.{workspace_id}", "order": "created_at.desc"})
    if not artifacts:
        artifacts = [x for x in _ARTIFACTS.values() if x["workspace_id"] == workspace_id]
    return {"workspace": workspace, "tasks": tasks, "artifacts": artifacts}


@router.post("/workspaces/{workspace_id}/tasks")
async def create_task(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    task = {"id": str(uuid4()), "workspace_id": workspace_id, "title": str(payload.get("title") or "Nueva tarea"), "prompt": str(payload.get("prompt") or ""), "capability": str(payload.get("capability") or "chat"), "status": "queued", "metadata": payload.get("metadata") or {}, "created_at": _now(), "updated_at": _now()}
    rows = await _db("POST", "workspace_tasks", json=task)
    if rows:
        task = rows[0]
    _TASKS[task["id"]] = task
    return task


@router.post("/workspaces/{workspace_id}/artifacts")
async def create_artifact(workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    artifact = {"id": str(uuid4()), "workspace_id": workspace_id, "name": str(payload.get("name") or "Nuevo artefacto"), "artifact_type": str(payload.get("artifact_type") or "document"), "status": "draft", "content": payload.get("content"), "metadata": payload.get("metadata") or {}, "created_at": _now(), "updated_at": _now()}
    rows = await _db("POST", "workspace_artifacts", json=artifact)
    if rows:
        artifact = rows[0]
    _ARTIFACTS[artifact["id"]] = artifact
    return artifact


@router.get("/workspaces/{workspace_id}/artifacts")
async def list_artifacts(workspace_id: str) -> dict[str, Any]:
    rows = await _db("GET", "workspace_artifacts", params={"select": "*", "workspace_id": f"eq.{workspace_id}", "order": "updated_at.desc"})
    if not rows:
        rows = [x for x in _ARTIFACTS.values() if x["workspace_id"] == workspace_id]
    return {"artifacts": rows}
