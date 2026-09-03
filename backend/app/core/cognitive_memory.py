from __future__ import annotations

import os
import re
from typing import Any

import httpx


class CognitiveMemoryAdapter:
    """Best-effort bridge between Bitey's cognition loop and Supabase cognitive tables.

    The adapter is intentionally schema-tolerant: it reads rows with select=* and
    extracts only generic fields. If Supabase or a table is unavailable, cognition
    continues normally with an empty learned context.
    """

    TABLES = (
        "bitey_cognitive_nodes",
        "bitey_cognitive_edges",
        "bitey_cognitive_mastery",
        "bitey_cognitive_replay",
        "bitey_ai_evaluations",
        "bitey_learning_events",
    )

    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        self.timeout = float(os.getenv("COGNITIVE_MEMORY_TIMEOUT", "8"))
        self.limit = max(1, min(50, int(os.getenv("COGNITIVE_MEMORY_ROWS", "12"))))

    @property
    def persistent(self) -> bool:
        return bool(self.url and self.key)

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json",
        }

    async def _read_table(self, client: httpx.AsyncClient, table: str) -> list[dict[str, Any]]:
        response = await client.get(
            f"{self.url}/rest/v1/{table}",
            headers=self._headers(),
            params={"select": "*", "limit": str(self.limit)},
        )
        response.raise_for_status()
        data = response.json()
        return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"[\wáéíóúüñ]{3,}", text.lower()) if token not in {"para", "como", "que", "the", "and", "con", "una", "por"}}

    def _score(self, row: dict[str, Any], query_tokens: set[str]) -> int:
        haystack = " ".join(str(v) for v in row.values() if isinstance(v, (str, int, float, bool)))
        row_tokens = self._tokens(haystack)
        return len(query_tokens & row_tokens)

    async def retrieve(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.persistent:
            return {"enabled": False, "available": False, "records": {}, "summary": "Supabase cognitive memory is not configured."}

        query_tokens = self._tokens(message)
        records: dict[str, list[dict[str, Any]]] = {}
        errors: dict[str, str] = {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for table in self.TABLES:
                    try:
                        rows = await self._read_table(client, table)
                        ranked = sorted(rows, key=lambda row: self._score(row, query_tokens), reverse=True)
                        relevant = [row for row in ranked if self._score(row, query_tokens) > 0][: min(5, self.limit)]
                        records[table] = relevant or rows[: min(2, self.limit)]
                    except Exception as exc:
                        errors[table] = type(exc).__name__
        except Exception as exc:
            return {"enabled": True, "available": False, "records": {}, "errors": {"connection": type(exc).__name__}, "summary": "Cognitive memory unavailable; continuing without learned context."}

        counts = {table: len(rows) for table, rows in records.items()}
        available = bool(records)
        return {
            "enabled": True,
            "available": available,
            "records": records,
            "counts": counts,
            "errors": errors,
            "summary": "Learned cognitive context retrieved." if available else "No learned cognitive context available yet.",
        }

    @staticmethod
    def compact_for_prompt(memory: dict[str, Any], max_chars: int = 5000) -> str:
        if not memory.get("available"):
            return ""
        chunks: list[str] = []
        for table, rows in (memory.get("records") or {}).items():
            for row in rows[:5]:
                compact = {k: v for k, v in row.items() if k not in {"created_at", "updated_at", "id"}}
                text = f"{table}: {compact}"
                chunks.append(text[:900])
        result = "\n".join(chunks)
        return result[:max_chars]
