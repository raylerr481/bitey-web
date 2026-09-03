"""Compatibility shim: Neo4j is retired from Bitey IA Web.

Knowledge relationships are now represented through the canonical
Supabase/PostgreSQL knowledge layer. This module performs no graph-network
access and exists only to prevent legacy imports from crashing the service.
"""
from __future__ import annotations
from typing import Any

class Neo4jAdapter:
    enabled = False
    configured = False

    async def close(self) -> None:
        return None

    async def health(self) -> dict[str, Any]:
        return {"enabled": False, "configured": False, "status": "retired", "replacement": "supabase_postgres"}

    async def related_context(self, query: str) -> dict[str, Any]:
        return {"available": False, "results": [], "reason": "neo4j_retired", "replacement": "supabase_postgres"}

    async def write_experience(self, **kwargs: Any) -> bool:
        return False
