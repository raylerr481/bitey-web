from __future__ import annotations

from typing import Any

from .task_contract import TaskContract

CONTRACT_METADATA_KEY = "task_contract"
CONTRACT_VERSION = 1


def contract_from_task(task: dict[str, Any]) -> TaskContract:
    """Rehydrate the universal contract from persisted task metadata/result."""
    metadata = task.get("metadata") or {}
    raw = metadata.get(CONTRACT_METADATA_KEY) or {}
    if not raw:
        result = task.get("result") or {}
        raw = result.get("task_contract") or {}

    if raw:
        data = dict(raw)
        data.pop("version", None)
        data.setdefault("task_id", str(task.get("id")))
        data.setdefault("prompt", str(task.get("prompt") or ""))
        data.setdefault("capability", str(task.get("capability") or "chat"))
        data.setdefault("retry_count", int(metadata.get("retry_count") or 0))
        return TaskContract(**data)

    return TaskContract(
        task_id=str(task.get("id")),
        prompt=str(task.get("prompt") or ""),
        capability=str(task.get("capability") or "chat"),
        budget={"paid_inference": False, "max_retries": int(metadata.get("max_retries", 2))},
        retry_count=int(metadata.get("retry_count") or 0),
    )


def persist_contract(task: dict[str, Any], contract: TaskContract) -> dict[str, Any]:
    """Store a versioned contract snapshot in the existing JSON metadata column."""
    metadata = dict(task.get("metadata") or {})
    metadata[CONTRACT_METADATA_KEY] = {"version": CONTRACT_VERSION, **contract.to_dict()}
    metadata["retry_count"] = contract.retry_count
    task["metadata"] = metadata
    return task


def sync_contract_from_execution(task: dict[str, Any], execution: dict[str, Any]) -> TaskContract:
    """Prefer the authoritative runtime contract, then persist it on the task."""
    raw = execution.get("task_contract") or {}
    if raw:
        data = dict(raw)
        data.pop("version", None)
        data.setdefault("task_id", str(task.get("id")))
        contract = TaskContract(**data)
    else:
        contract = contract_from_task(task)
    persist_contract(task, contract)
    return contract
