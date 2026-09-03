"""Optional Neo4j knowledge/relationship capability for Bitey IA.

Neo4j is not a second brain. It is a cognitive support component used to
retrieve structured relationships and graph context for the central Bitey
Cognitive Core. The adapter is fail-safe: when disabled or unavailable,
Bitey continues operating with its other memory/context providers.
"""

from __future__ import annotations

import os
from typing import Any


class Neo4jAdapter:
    """Small, provider-agnostic Neo4j adapter with graceful degradation."""

    def __init__(self) -> None:
        self.enabled = os.getenv("NEO4J_ENABLED", "false").lower() == "true"
        self.uri = os.getenv("NEO4J_URI", "")
        self.username = os.getenv("NEO4J_USERNAME", "")
        self.password = os.getenv("NEO4J_PASSWORD", "")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")
        self.max_results = max(1, int(os.getenv("NEO4J_MAX_RESULTS", "8")))
        self._driver = None
        self._error: str | None = None

        if self.enabled and self.uri and self.username and self.password:
            try:
                from neo4j import AsyncGraphDatabase
                self._driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.username, self.password),
                )
            except Exception as exc:  # optional dependency/runtime failure
                self._error = type(exc).__name__

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self._driver)

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()

    async def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "configured": False, "status": "disabled"}
        if not self._driver:
            return {"enabled": True, "configured": False, "status": "not_configured", "error": self._error}
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 AS ok")
                record = await result.single()
                return {"enabled": True, "configured": True, "status": "connected", "database": self.database, "probe": bool(record and record["ok"] == 1)}
        except Exception as exc:
            return {"enabled": True, "configured": True, "status": "unavailable", "database": self.database, "error": type(exc).__name__}

    async def related_context(self, query: str) -> dict[str, Any]:
        """Return lightweight graph context around text-matching knowledge nodes."""
        if not self.configured or not query.strip():
            return {"available": False, "results": [], "reason": "neo4j_unavailable"}
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
            return {"available": True, "results": rows, "count": len(rows)}
        except Exception as exc:
            return {"available": False, "results": [], "reason": type(exc).__name__}

    async def write_experience(self, *, experience_id: str, domain: str, summary: str, metadata: dict[str, Any] | None = None) -> bool:
        """Persist a bounded cognitive experience without storing secrets."""
        if not self.configured:
            return False
        cypher = """
        MERGE (e:Experience {id: $id})
        SET e.domain = $domain, e.summary = $summary
        SET e.updated_at = datetime()
        RETURN e.id AS id
        """
        try:
            async with self._driver.session(database=self.database) as session:
                await session.run(cypher, id=experience_id, domain=domain[:100], summary=summary[:4000])
            return True
        except Exception:
            return False
