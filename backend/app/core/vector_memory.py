"""Optional semantic memory layer for Bitey.

The adapter accepts embeddings produced by any configured embedding provider.
It deliberately does not own embedding generation, allowing Bitey to switch
models without changing its memory architecture.
"""
from __future__ import annotations

import os
from typing import Any


class QdrantVectorMemory:
    def __init__(self) -> None:
        self.enabled = os.getenv("QDRANT_ENABLED", "false").lower() == "true"
        self.url = os.getenv("QDRANT_URL", "http://127.0.0.1:6333").rstrip("/")
        self.api_key = os.getenv("QDRANT_API_KEY", "").strip()
        self.collection = os.getenv("QDRANT_COLLECTION", "bitey_memory").strip()
        self.vector_size = int(os.getenv("QDRANT_VECTOR_SIZE", "384"))
        self.timeout = float(os.getenv("QDRANT_TIMEOUT", "5"))
        self._client = None
        self._error: str | None = None
        if self.enabled:
            try:
                from qdrant_client import AsyncQdrantClient
                self._client = AsyncQdrantClient(url=self.url, api_key=self.api_key or None, timeout=self.timeout)
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
            await self._client.get_collections()
            return {"enabled": True, "configured": True, "status": "connected", "collection": self.collection, "vector_size": self.vector_size}
        except Exception as exc:
            return {"enabled": True, "configured": True, "status": "unavailable", "error": type(exc).__name__}

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()

    async def ensure_collection(self) -> bool:
        if not self.configured:
            return False
        try:
            from qdrant_client.models import Distance, VectorParams
            collections = await self._client.get_collections()
            names = {c.name for c in collections.collections}
            if self.collection not in names:
                await self._client.create_collection(self.collection, vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE))
            return True
        except Exception:
            return False

    async def search(self, vector: list[float], limit: int = 8) -> list[dict[str, Any]]:
        if not self.configured or len(vector) != self.vector_size:
            return []
        try:
            results = await self._client.search(collection_name=self.collection, query_vector=vector, limit=max(1, min(50, limit)))
            return [{"id": str(item.id), "score": float(item.score), "payload": item.payload or {}} for item in results]
        except Exception:
            return []
