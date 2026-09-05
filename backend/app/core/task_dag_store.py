from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .task_dag import TaskDAG, dag_from_plan

DAG_METADATA_KEY = "task_dag"
DAG_VERSION = 1


def dag_from_task(task: dict[str, Any]) -> TaskDAG | None:
    """Rehydrate a DAG from workspace_tasks.metadata without creating a new plan."""
    metadata = task.get("metadata") or {}
    raw = metadata.get(DAG_METADATA_KEY)
    if not raw:
        result = task.get("result") or {}
        raw = result.get(DAG_METADATA_KEY)
    if not raw:
        return None
    data = dict(raw)
    data.pop("version", None)
    dag = TaskDAG.from_dict(data)
    return dag


def persist_dag(task: dict[str, Any], dag: TaskDAG) -> dict[str, Any]:
    """Store a compact, versioned DAG snapshot in the existing JSON metadata."""
    dag.validate()
    metadata = dict(task.get("metadata") or {})
    metadata[DAG_METADATA_KEY] = {"version": DAG_VERSION, **dag.to_dict()}
    metadata["dag_updated_at"] = datetime.now(timezone.utc).isoformat()
    task["metadata"] = metadata
    return task


def dag_or_build(task: dict[str, Any], plan: list[dict[str, Any]]) -> tuple[TaskDAG, bool]:
    """Return the persisted DAG when valid; otherwise build it once from the plan."""
    existing = dag_from_task(task)
    if existing is not None:
        existing.reset_running()
        return existing, True
    return dag_from_plan(plan), False
