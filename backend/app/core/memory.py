from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class MemoryStore:
    """Conversation memory with Supabase persistence when configured.

    The in-process cache remains the fast path. Supabase is the durable store.
    The service-role key must stay server-side and is never exposed to the web UI.
    """

    conversations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    @property
    def persistent(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    async def create_conversation(self, conversation_id: str, metadata: dict[str, Any] | None = None) -> None:
        self.conversations.setdefault(conversation_id, [])
        if not self.persistent:
            return
        payload = {"id": conversation_id, "metadata": metadata or {}}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.supabase_url}/rest/v1/conversations",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()

    async def append(self, conversation_id: str, message: dict[str, Any]) -> None:
        self.conversations.setdefault(conversation_id, []).append(message)
        if not self.persistent:
            return
        payload = {
            "conversation_id": conversation_id,
            "role": message["role"],
            "content": message["content"],
            "metadata": message.get("metadata", {}),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.supabase_url}/rest/v1/messages",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()

    async def history(self, conversation_id: str) -> list[dict[str, Any]]:
        if self.persistent:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/messages",
                    headers=self._headers(),
                    params={
                        "conversation_id": f"eq.{conversation_id}",
                        "select": "role,content,created_at",
                        "order": "created_at.asc",
                    },
                )
                response.raise_for_status()
                rows = response.json()
                if rows:
                    self.conversations[conversation_id] = [
                        {"role": row["role"], "content": row["content"]} for row in rows
                    ]
        return list(self.conversations.get(conversation_id, []))

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
