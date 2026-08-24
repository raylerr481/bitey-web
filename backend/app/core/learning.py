from __future__ import annotations

import hashlib
import os
from typing import Any

import httpx


class LearningEngine:
    """Safe incremental learning: observations become candidates before knowledge."""

    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    @property
    def persistent(self) -> bool:
        return bool(self.url and self.key)

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def observe(self, title: str, payload: dict[str, Any], source: str = "conversation", confidence: float = 0.5) -> dict[str, Any] | None:
        if not self.persistent:
            return None
        digest = hashlib.sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()
        row = {
            "candidate_type": "observation",
            "title": title,
            "payload": {**payload, "input_hash": digest},
            "confidence": max(0.0, min(1.0, confidence)),
            "source": source,
            "evidence_count": 1,
            "status": "pending",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.url}/rest/v1/cognitive_learning_candidates",
                headers=self._headers(),
                json=row,
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None

    async def record_cycle(self, trigger_source: str, observations: int = 1, improvements: int = 0, summary: dict[str, Any] | None = None) -> None:
        if not self.persistent:
            return
        row = {
            "status": "completed",
            "trigger_source": trigger_source,
            "observations": observations,
            "improvements": improvements,
            "evaluation_summary": summary or {},
            "completed_at": "now()",
        }
        # Supabase REST does not evaluate now() strings, so use an ordinary insert and let the DB default timestamp.
        row.pop("completed_at")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.url}/rest/v1/learning_cycles",
                headers=self._headers(),
                json=row,
            )
            response.raise_for_status()
