"""Optional MongoDB adapter for Bitey episodic/working memory.

MongoDB is a memory organ, never the executive brain. The adapter is disabled
unless explicitly configured and all failures degrade to the other memory
providers.
"""
from __future__ import annotations

import os
from typing import Any


class MongoMemoryAdapter:
    def __init__(self) -> None:
        self.enabled = os.getenv("MONGODB_ENABLED", "false").lower() == "true"
        self.uri = os.getenv("MONGODB_URI", "").strip()
        self.database = os.getenv("MONGODB_DATABASE", "bitey").strip()
        self.collection = os.getenv("MONGODB_MEMORY_COLLECTION", "cognitive_episodes").strip()
        self.timeout_ms = max(1000, int(os.getenv("MONGODB_TIMEOUT_MS", "4000")))
        self._client = None
        self._error: str | None = None
        if self.enabled and self.uri:
            try:
                from pymongo import AsyncMongoClient
                self._client = AsyncMongoClient(self.uri, serverSelectionTimeoutMS=self.timeout_ms)
            except Exception as exc:
                self._error = type(exc).__name__

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self._client)

    async def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "configured": False, "status": "disabled"}
        if not self._client:
            return {"enabled": True, "configured": False, "status": "not_configured", "error": self._error}
        try:
            await self._client.admin.command("ping")
            return {"enabled": True, "configured": True, "status": "connected", "database": self.database, "collection": self.collection}
        except Exception as exc:
            return {"enabled": True, "configured": True, "status": "unavailable", "error": type(exc).__name__}

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()

    async def remember(self, *, conversation_id: str, domain: str, summary: str, importance: float = 0.5, metadata: dict[str, Any] | None = None) -> bool:
        if not self.configured:
            return False
        try:
            await self._client[self.database][self.collection].insert_one({
                "conversation_id": conversation_id,
                "domain": domain[:100],
                "summary": summary[:4000],
                "importance": max(0.0, min(1.0, importance)),
                "metadata": metadata or {},
                "source": "bitey_brain",
            })
            return True
        except Exception:
            return False

    async def recall(self, *, conversation_id: str | None = None, domain: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        query: dict[str, Any] = {}
        if conversation_id:
            query["conversation_id"] = conversation_id
        if domain:
            query["domain"] = domain
        try:
            cursor = self._client[self.database][self.collection].find(query, {"_id": 0}).sort("importance", -1).limit(max(1, min(50, limit)))
            return await cursor.to_list(length=max(1, min(50, limit)))
        except Exception:
            return []
