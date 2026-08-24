from __future__ import annotations

import asyncio
import json
import os
import socket

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
WORKER_ID = f"supracerebro-{socket.gethostname()}"


def headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def claim(client: httpx.AsyncClient) -> list[dict]:
    response = await client.post(
        f"{SUPABASE_URL}/rest/v1/rpc/claim_cognitive_jobs",
        headers=headers(),
        json={"p_worker": WORKER_ID, "p_limit": 5},
    )
    response.raise_for_status()
    return response.json()


async def finish(client: httpx.AsyncClient, job_id: str, success: bool, error: str | None = None) -> None:
    response = await client.post(
        f"{SUPABASE_URL}/rest/v1/rpc/finish_cognitive_job",
        headers=headers(),
        json={"p_id": job_id, "p_success": success, "p_error": error},
    )
    response.raise_for_status()


async def process(client: httpx.AsyncClient, job: dict) -> None:
    """Process only safe background bookkeeping; model evaluation is delegated to future job handlers."""
    job_type = job.get("job_type")
    payload = job.get("payload") or {}

    if job_type == "learning_observation":
        await client.post(
            f"{SUPABASE_URL}/rest/v1/cognitive_learning_events",
            headers=headers(),
            json={
                "event_type": "background_observation",
                "source_type": payload.get("source_type", "conversation"),
                "source_ref": payload.get("source_ref"),
                "input_hash": payload.get("input_hash"),
                "changes": {"status": "observed", "payload": payload},
                "confidence": float(payload.get("confidence", 0.4)),
                "outcome": "queued_for_evaluation",
            },
        )
        return

    if job_type == "learning_cycle":
        await client.post(
            f"{SUPABASE_URL}/rest/v1/learning_cycles",
            headers=headers(),
            json={
                "status": "completed",
                "trigger_source": "background_worker",
                "observations": int(payload.get("observations", 0)),
                "improvements": int(payload.get("improvements", 0)),
                "evaluation_summary": payload.get("evaluation_summary", {}),
                "completed_at": None,
            },
        )
        return

    raise ValueError(f"unknown_job_type:{job_type}")


async def main() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

    async with httpx.AsyncClient(timeout=30) as client:
        jobs = await claim(client)
        for job in jobs:
            try:
                await process(client, job)
                await finish(client, job["id"], True)
            except Exception as exc:
                await finish(client, job["id"], False, str(exc)[:1000])


if __name__ == "__main__":
    asyncio.run(main())
