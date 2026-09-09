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

    When an execution scope is present, cognitive rows are accepted only when they
    carry the same ``memory_scope``. This prevents learned context from one tenant,
    user, module, or conversation being reused in another scope.
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

    @staticmethod
    def _extract_memory_scope(context: dict[str, Any] | None) -> str | None:
        """Read only a server-produced scope from the assembled context."""
        if not isinstance(context, dict):
            return None

        candidates: list[Any] = [context.get("memory_scope")]
        for key in ("execution", "memory"):
            nested = context.get(key)
            if isinstance(nested, dict):
                candidates.append(nested.get("memory_scope"))

        execution_context = context.get("execution_context")
        if isinstance(execution_context, dict):
            candidates.append(execution_context.get("memory_scope"))
            memory = execution_context.get("memory")
            if isinstance(memory, dict):
                candidates.append(memory.get("memory_scope"))

        for value in candidates:
            scope = str(value).strip() if value is not None else ""
            if scope:
                return scope
        return None

    @staticmethod
    def _row_memory_scope(row: dict[str, Any]) -> str | None:
        """Extract the persisted scope without trusting arbitrary row content as scope."""
        for key in ("memory_scope", "execution_scope"):
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        metadata = row.get("metadata")
        if isinstance(metadata, dict):
            value = metadata.get("memory_scope")
            if isinstance(value, str) and value.strip():
                return value.strip()
            execution_scope = metadata.get("execution_scope")
            if isinstance(execution_scope, dict):
                value = execution_scope.get("memory_scope")
                if isinstance(value, str) and value.strip():
                    return value.strip()

        return None

    @classmethod
    def _filter_scope(cls, rows: list[dict[str, Any]], memory_scope: str | None) -> list[dict[str, Any]]:
        """Apply fail-closed isolation whenever a scope is available."""
        if not memory_scope:
            return rows
        return [row for row in rows if cls._row_memory_scope(row) == memory_scope]

    async def retrieve(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.persistent:
            return {"enabled": False, "available": False, "records": {}, "summary": "Supabase cognitive memory is not configured."}

        query_tokens = self._tokens(message)
        memory_scope = self._extract_memory_scope(context)
        records: dict[str, list[dict[str, Any]]] = {}
        errors: dict[str, str] = {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for table in self.TABLES:
                    try:
                        rows = await self._read_table(client, table)
                        rows = self._filter_scope(rows, memory_scope)
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
            "memory_scope": memory_scope,
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
