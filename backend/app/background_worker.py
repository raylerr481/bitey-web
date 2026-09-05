from __future__ import annotations

import asyncio
import os
import socket
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
WORKER_ID = f"bitey-worker-{socket.gethostname()}"
WORKSPACE_RECOVERY_STALE_SECONDS = max(60, int(os.getenv("BITEY_WORKSPACE_RECOVERY_STALE_SECONDS", "300")))


def headers() -> dict[str, str]:
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}


async def claim(client: httpx.AsyncClient) -> list[dict]:
    response = await client.post(f"{SUPABASE_URL}/rest/v1/rpc/claim_cognitive_jobs", headers=headers(), json={"p_worker": WORKER_ID, "p_limit": 5})
    response.raise_for_status()
    return response.json()


async def finish(client: httpx.AsyncClient, job_id: str, success: bool, error: str | None = None) -> None:
    response = await client.post(f"{SUPABASE_URL}/rest/v1/rpc/finish_cognitive_job", headers=headers(), json={"p_id": job_id, "p_success": success, "p_error": error})
    response.raise_for_status()


async def recover_stale_workspace_tasks(*, stale_seconds: int = WORKSPACE_RECOVERY_STALE_SECONDS) -> dict[str, int]:
    """Requeue stale workspace tasks using an optimistic compare-and-swap takeover.

    A task is eligible only when it is still running, older than the stale
    threshold, and has a persisted TaskDAG. The exact updated_at value is used
    as the CAS guard so two workers cannot both take over the same row.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"scanned": 0, "recovered": 0, "skipped": 0}

    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=max(60, stale_seconds))).isoformat()
    params = {
        "select": "*",
        "status": "eq.running",
        "updated_at": f"lt.{cutoff}",
        "order": "updated_at.asc",
        "limit": "20",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{SUPABASE_URL}/rest/v1/workspace_tasks", headers=headers(), params=params)
        response.raise_for_status()
        tasks = response.json()

        recovered = 0
        skipped = 0
        for task in tasks:
            metadata = task.get("metadata") or {}
            if not metadata.get("task_dag"):
                skipped += 1
                continue
            task_id = str(task.get("id") or "")
            workspace_id = str(task.get("workspace_id") or "")
            previous_updated_at = str(task.get("updated_at") or "")
            if not task_id or not workspace_id or not previous_updated_at:
                skipped += 1
                continue

            now = datetime.now(timezone.utc).isoformat()
            recovery = dict(metadata.get("recovery") or {})
            recovery.update({
                "reason": "stale_running_task",
                "recovered_at": now,
                "previous_execution_token": task.get("execution_token"),
            })
            new_metadata = dict(metadata)
            new_metadata["recovery"] = recovery

            # CAS: only the worker that still sees this exact running row wins.
            cas_params = {
                "id": f"eq.{task_id}",
                "workspace_id": f"eq.{workspace_id}",
                "status": "eq.running",
                "updated_at": f"eq.{previous_updated_at}",
            }
            takeover = await client.patch(
                f"{SUPABASE_URL}/rest/v1/workspace_tasks",
                headers=headers(),
                params=cas_params,
                json={
                    "status": "queued",
                    "execution_token": None,
                    "started_at": None,
                    "completed_at": None,
                    "updated_at": now,
                    "metadata": new_metadata,
                },
            )
            takeover.raise_for_status()
            if not takeover.json():
                skipped += 1
                continue

            recovered_task = takeover.json()[0]
            try:
                # Import lazily to avoid the workspace API/background worker
                # initialization cycle. The normal run path performs the real
                # atomic claim and then rehydrates the persisted DAG.
                from .workspace_api import _execute_task
                await _execute_task(workspace_id, task_id, recovered_task)
                recovered += 1
            except Exception:
                # _execute_task owns terminal failure handling. The recovery
                # loop must remain alive and can retry the task on a later pass.
                skipped += 1

        return {"scanned": len(tasks), "recovered": recovered, "skipped": skipped}


async def process(client: httpx.AsyncClient, job: dict) -> None:
    job_type = job.get("job_type")
    payload = job.get("payload") or {}
    if job_type == "learning_observation":
        response = await client.post(f"{SUPABASE_URL}/rest/v1/cognitive_learning_events", headers=headers(), json={
            "event_type": "background_observation",
            "source_type": payload.get("source_type", "conversation"),
            "source_ref": payload.get("source_ref"),
            "input_hash": payload.get("input_hash"),
            "changes": {"status": "observed", "payload": payload},
            "confidence": float(payload.get("confidence", 0.4)),
            "outcome": "queued_for_evaluation",
        })
        response.raise_for_status()
        return
    if job_type == "learning_cycle":
        response = await client.post(f"{SUPABASE_URL}/rest/v1/learning_cycles", headers=headers(), json={
            "status": "completed", "trigger_source": "background_worker",
            "observations": int(payload.get("observations", 0)),
            "improvements": int(payload.get("improvements", 0)),
            "evaluation_summary": payload.get("evaluation_summary", {}),
        })
        response.raise_for_status()
        return
    raise ValueError(f"unknown_job_type:{job_type}")


async def process_once() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return 0
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            await recover_stale_workspace_tasks()
        except Exception:
            # Recovery is best-effort and must not stop the existing cognitive job worker.
            pass
        jobs = await claim(client)
        for job in jobs:
            try:
                await process(client, job)
                await finish(client, job["id"], True)
            except Exception as exc:
                await finish(client, job["id"], False, str(exc)[:1000])
        return len(jobs)


async def main() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    await process_once()


if __name__ == "__main__":
    asyncio.run(main())
