from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .task_dag import TaskDAG, dag_from_plan

DAG_METADATA_KEY = "task_dag"
DAG_VERSION = 1


def dag_from_task(task: dict[str, Any]) -> TaskDAG | None:
    """Rehydrate a DAG from workspace_tasks.metadata without creating a new plan."""
    metadata = task.get("metadata") or {}
    raw = metadata.get(DAG_METADATA_KEY) or (task.get("result") or {}).get(DAG_METADATA_KEY)
    if not raw:
        return None
    data = dict(raw); data.pop("version", None)
    return TaskDAG.from_dict(data)


def persist_dag(task: dict[str, Any], dag: TaskDAG) -> dict[str, Any]:
    """Store a compact, versioned DAG snapshot in the existing JSON metadata."""
    dag.validate()
    metadata = dict(task.get("metadata") or {})
    metadata[DAG_METADATA_KEY] = {"version": DAG_VERSION, **dag.to_dict()}
    metadata["dag_updated_at"] = datetime.now(timezone.utc).isoformat()
    task["metadata"] = metadata
    return task


async def persist_dag_to_supabase(*, workspace_id: str, task_id: str, metadata: dict[str, Any], dag: TaskDAG) -> bool:
    """Durably checkpoint a DAG without adding a new table or paid service."""
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return False
    holder = {"metadata": metadata}
    persist_dag(holder, dag)
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=minimal"}
    params = {"id": f"eq.{task_id}", "workspace_id": f"eq.{workspace_id}"}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.patch(f"{url}/rest/v1/workspace_tasks", headers=headers, params=params, json={"metadata": holder["metadata"], "updated_at": datetime.now(timezone.utc).isoformat()})
        response.raise_for_status()
    return True


def dag_or_build(task: dict[str, Any], plan: list[dict[str, Any]]) -> tuple[TaskDAG, bool]:
    """Return the persisted DAG when valid; otherwise build it once from the plan."""
    existing = dag_from_task(task)
    if existing is not None:
        existing.reset_running()
        return existing, True
    return dag_from_plan(plan), False
