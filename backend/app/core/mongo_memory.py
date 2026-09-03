"""Compatibility shim: MongoDB is retired from Bitey IA Web.

Supabase/PostgreSQL is the canonical persistence layer. This shim remains
only temporarily so older imports cannot crash the application; it performs
no network access and never stores data.
"""
from __future__ import annotations
from typing import Any

class MongoMemoryAdapter:
    enabled = False
    configured = False

    async def health(self) -> dict[str, Any]:
        return {"enabled": False, "configured": False, "status": "retired", "replacement": "supabase_postgres"}

    async def close(self) -> None:
        return None

    async def remember(self, **kwargs: Any) -> bool:
        return False

    async def recall(self, **kwargs: Any) -> list[dict[str, Any]]:
        return []
