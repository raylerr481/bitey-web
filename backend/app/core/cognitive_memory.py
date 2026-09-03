from __future__ import annotations

import os
import re
from typing import Any

import httpx


class CognitiveMemoryAdapter:
    """Supabase-native cognitive memory for Bitey IA.

    The dedicated ``bitey`` schema is canonical. MongoDB/Neo4j/Qdrant are not
    required for cognition. Retrieval is intentionally schema-aware and keeps
    a lexical fallback until an embedding RPC is enabled.
    """

    TABLES = ("memories", "knowledge_nodes", "evidence", "evaluations", "learning_events")

    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        self.schema = "bitey"
        self.timeout = float(os.getenv("COGNITIVE_MEMORY_TIMEOUT", "8"))
        self.limit = max(1, min(50, int(os.getenv("COGNITIVE_MEMORY_ROWS", "20"))))

    @property
    def persistent(self) -> bool:
        return bool(self.url and self.key)

    def _headers(self, content_type: bool = False) -> dict[str, str]:
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json",
            "Accept-Profile": self.schema,
            "Content-Profile": self.schema,
        }
        if content_type:
            headers["Content-Type"] = "application/json"
            headers["Prefer"] = "return=representation"
        return headers

    async def _read_table(self, client: httpx.AsyncClient, table: str, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
        response = await client.get(
            f"{self.url}/rest/v1/{table}",
            headers=self._headers(),
            params=params or {"select": "*", "limit": str(self.limit)},
        )
        response.raise_for_status()
        data = response.json()
        return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []

    @staticmethod
    def _tokens(text: str) -> set[str]:
        stop = {"para", "como", "que", "the", "and", "con", "una", "por", "los", "las", "del", "una", "this", "that"}
        return {token for token in re.findall(r"[\wáéíóúüñ]{3,}", text.lower()) if token not in stop}

    def _score(self, row: dict[str, Any], query_tokens: set[str]) -> int:
        haystack = " ".join(str(v) for v in row.values() if isinstance(v, (str, int, float, bool)))
        return len(query_tokens & self._tokens(haystack))

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
                        relevant = [row for row in ranked if self._score(row, query_tokens) > 0][: min(6, self.limit)]
                        if relevant:
                            records[table] = relevant
                    except Exception as exc:
                        errors[table] = type(exc).__name__
        except Exception as exc:
            return {"enabled": True, "available": False, "records": {}, "errors": {"connection": type(exc).__name__}, "summary": "Cognitive memory unavailable; continuing without learned context."}

        return {
            "enabled": True,
            "available": bool(records),
            "records": records,
            "counts": {table: len(rows) for table, rows in records.items()},
            "errors": errors,
            "summary": "Learned cognitive context retrieved." if records else "No learned cognitive context available yet.",
        }

    async def knowledge_context(self, query: str, limit: int = 8) -> dict[str, Any]:
        """Retrieve a lightweight relational context from Postgres knowledge nodes/edges."""
        if not self.persistent:
            return {"available": False, "results": [], "source": "supabase"}
        tokens = self._tokens(query)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                nodes = await self._read_table(client, "knowledge_nodes", {"select": "*", "limit": str(self.limit)})
                ranked = sorted(nodes, key=lambda row: self._score(row, tokens), reverse=True)
                selected = [n for n in ranked if self._score(n, tokens) > 0][: max(1, min(12, limit))]
                results = []
                for node in selected:
                    node_id = node.get("id")
                    edges = await self._read_table(client, "knowledge_edges", {"select": "*", "or": f"source_node_id.eq.{node_id},target_node_id.eq.{node_id}", "limit": "20"}) if node_id else []
                    results.append({"node": node, "relations": edges})
                return {"available": bool(results), "count": len(results), "results": results, "source": "supabase.bitey.knowledge"}
        except Exception as exc:
            return {"available": False, "results": [], "source": "supabase", "error": type(exc).__name__}

    async def record_evaluation(self, session_id: str | None, input_text: str, output_text: str, evaluation: dict[str, Any]) -> bool:
        return await self._insert("evaluations", {
            "session_id": session_id,
            "input_text": input_text,
            "output_text": output_text,
            "confidence": evaluation.get("confidence"),
            "contradiction_detected": bool(evaluation.get("contradiction_detected", False)),
            "policy_status": evaluation.get("policy_status"),
            "evaluator": "bitey-evaluation-engine",
            "details": evaluation,
        })

    async def record_learning_event(self, session_id: str | None, event_type: str, observation: dict[str, Any], outcome: dict[str, Any] | None = None) -> bool:
        return await self._insert("learning_events", {
            "session_id": session_id,
            "event_type": event_type,
            "observation": observation,
            "outcome": outcome or {},
        })

    async def _insert(self, table: str, payload: dict[str, Any]) -> bool:
        if not self.persistent:
            return False
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.url}/rest/v1/{table}", headers=self._headers(content_type=True), json=payload)
                response.raise_for_status()
            return True
        except Exception:
            return False

    @staticmethod
    def compact_for_prompt(memory: dict[str, Any], max_chars: int = 6000) -> str:
        if not memory.get("available"):
            return ""
        chunks: list[str] = []
        for table, rows in (memory.get("records") or {}).items():
            for row in rows[:6]:
                compact = {k: v for k, v in row.items() if k not in {"created_at", "updated_at", "id", "embedding"}}
                chunks.append(f"{table}: {compact}"[:1000])
        return "\n".join(chunks)[:max_chars]
