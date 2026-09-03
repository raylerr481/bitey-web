"""Legacy graph adapter with a Supabase-first knowledge fallback.

Bitey IA no longer requires Neo4j for cognition. When Neo4j is disabled,
related_context reads the canonical bitey.knowledge_nodes and
bitey.knowledge_edges tables in Supabase. The class name remains temporarily
for compatibility with the existing application wiring.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx


class Neo4jAdapter:
    """Compatibility adapter; canonical knowledge storage is Supabase."""

    def __init__(self) -> None:
        self.enabled = os.getenv("NEO4J_ENABLED", "false").lower() == "true"
        self.uri = os.getenv("NEO4J_URI", "")
        self.username = os.getenv("NEO4J_USERNAME", "")
        self.password = os.getenv("NEO4J_PASSWORD", "")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")
        self.max_results = max(1, int(os.getenv("NEO4J_MAX_RESULTS", "8")))
        self._driver = None
        self._error: str | None = None
        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

        if self.enabled and self.uri and self.username and self.password:
            try:
                from neo4j import AsyncGraphDatabase
                self._driver = AsyncGraphDatabase.driver(self.uri, auth=(self.username, self.password))
            except Exception as exc:
                self._error = type(exc).__name__

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self._driver)

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()

    async def health(self) -> dict[str, Any]:
        if self.configured:
            try:
                async with self._driver.session(database=self.database) as session:
                    result = await session.run("RETURN 1 AS ok")
                    record = await result.single()
                    return {"enabled": True, "configured": True, "status": "connected", "database": self.database, "probe": bool(record and record["ok"] == 1), "canonical_source": "neo4j_legacy"}
            except Exception as exc:
                return {"enabled": True, "configured": True, "status": "unavailable", "database": self.database, "error": type(exc).__name__}
        return {"enabled": False, "configured": False, "status": "disabled", "canonical_source": "supabase.bitey.knowledge" if self.supabase_configured else "unavailable"}

    @staticmethod
    def _tokens(text: str) -> set[str]:
        stop = {"para", "como", "que", "the", "and", "con", "una", "por", "los", "las", "del", "this", "that"}
        return {x for x in re.findall(r"[\wáéíóúüñ]{3,}", text.lower()) if x not in stop}

    @classmethod
    def _score(cls, row: dict[str, Any], tokens: set[str]) -> int:
        text = " ".join(str(v) for v in row.values() if isinstance(v, (str, int, float, bool)))
        return len(tokens & cls._tokens(text))

    async def _supabase_context(self, query: str) -> dict[str, Any]:
        if not self.supabase_configured or not query.strip():
            return {"available": False, "results": [], "reason": "supabase_unavailable"}
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Accept": "application/json",
            "Accept-Profile": "bitey",
        }
        tokens = self._tokens(query)
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/knowledge_nodes",
                    headers=headers,
                    params={"select": "*", "limit": "50"},
                )
                response.raise_for_status()
                nodes = response.json() if isinstance(response.json(), list) else []
                ranked = sorted(nodes, key=lambda row: self._score(row, tokens), reverse=True)
                selected = [n for n in ranked if self._score(n, tokens) > 0][: self.max_results]
                results = []
                for node in selected:
                    node_id = node.get("id")
                    if not node_id:
                        continue
                    edge_response = await client.get(
                        f"{self.supabase_url}/rest/v1/knowledge_edges",
                        headers=headers,
                        params={"select": "*", "or": f"source_node_id.eq.{node_id},target_node_id.eq.{node_id}", "limit": "20"},
                    )
                    edge_response.raise_for_status()
                    edges = edge_response.json() if isinstance(edge_response.json(), list) else []
                    results.append({"node": node, "relations": edges})
                return {"available": bool(results), "results": results, "count": len(results), "source": "supabase.bitey.knowledge"}
        except Exception as exc:
            return {"available": False, "results": [], "source": "supabase.bitey.knowledge", "reason": type(exc).__name__}

    async def related_context(self, query: str) -> dict[str, Any]:
        """Use Neo4j only when explicitly configured; otherwise use canonical Supabase knowledge."""
        if not self.configured:
            return await self._supabase_context(query)
        cypher = """
        MATCH (n)
        WHERE any(k IN keys(n) WHERE toString(n[k]) CONTAINS $query)
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN labels(n) AS labels, properties(n) AS node,
               type(r) AS relationship, labels(m) AS related_labels,
               properties(m) AS related_node
        LIMIT $limit
        """
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(cypher, query=query.strip()[:500], limit=self.max_results)
                rows = await result.data()
            return {"available": True, "results": rows, "count": len(rows), "source": "neo4j_legacy"}
        except Exception as exc:
            return {"available": False, "results": [], "reason": type(exc).__name__}

    async def write_experience(self, *, experience_id: str, domain: str, summary: str, metadata: dict[str, Any] | None = None) -> bool:
        if not self.configured:
            return False
        cypher = """
        MERGE (e:Experience {id: $id})
        SET e.domain = $domain, e.summary = $summary, e.updated_at = datetime()
        RETURN e.id AS id
        """
        try:
            async with self._driver.session(database=self.database) as session:
                await session.run(cypher, id=experience_id, domain=domain[:100], summary=summary[:4000])
            return True
        except Exception:
            return False
