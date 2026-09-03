from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class MemoryStore:
    """Durable conversation memory backed by the dedicated ``bitey`` schema."""

    conversations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    sessions: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        self.schema = "bitey"

    @property
    def persistent(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    def _headers(self, content_type: bool = False) -> dict[str, str]:
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Accept": "application/json",
            "Accept-Profile": self.schema,
            "Content-Profile": self.schema,
        }
        if content_type:
            headers["Content-Type"] = "application/json"
            headers["Prefer"] = "return=representation"
        return headers

    async def create_conversation(self, conversation_id: str, metadata: dict[str, Any] | None = None) -> None:
        self.conversations.setdefault(conversation_id, [])
        if not self.persistent:
            return
        payload = {
            "external_session_id": conversation_id,
            "user_ref": str((metadata or {}).get("user_ref") or ""),
            "language": str((metadata or {}).get("language") or "pt-BR"),
            "metadata": metadata or {},
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{self.supabase_url}/rest/v1/cognitive_sessions", headers=self._headers(True), json=payload)
                response.raise_for_status()
                rows = response.json()
                if isinstance(rows, list) and rows and rows[0].get("id"):
                    self.sessions[conversation_id] = str(rows[0]["id"])
        except Exception:
            # Conversation remains usable through the in-process cache.
            return

    async def _session_id(self, conversation_id: str) -> str | None:
        if conversation_id in self.sessions:
            return self.sessions[conversation_id]
        if not self.persistent:
            return None
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/cognitive_sessions",
                    headers=self._headers(),
                    params={"external_session_id": f"eq.{conversation_id}", "select": "id", "limit": "1"},
                )
                response.raise_for_status()
                rows = response.json()
                if isinstance(rows, list) and rows:
                    self.sessions[conversation_id] = str(rows[0]["id"])
                    return self.sessions[conversation_id]
        except Exception:
            return None
        return None

    async def append(self, conversation_id: str, message: dict[str, Any]) -> None:
        self.conversations.setdefault(conversation_id, []).append(message)
        if not self.persistent:
            return
        session_id = await self._session_id(conversation_id)
        if not session_id:
            return
        payload = {
            "session_id": session_id,
            "memory_type": "conversation_message",
            "content": str(message.get("content") or ""),
            "summary": str(message.get("content") or "")[:500],
            "source": "conversation",
            "confidence": 1.0,
            "importance": 0.5,
            "metadata": {"role": message.get("role", "user"), **(message.get("metadata") or {})},
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{self.supabase_url}/rest/v1/memories", headers=self._headers(True), json=payload)
                response.raise_for_status()
        except Exception:
            return

    async def history(self, conversation_id: str) -> list[dict[str, Any]]:
        if self.persistent:
            session_id = await self._session_id(conversation_id)
            if session_id:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        response = await client.get(
                            f"{self.supabase_url}/rest/v1/memories",
                            headers=self._headers(),
                            params={
                                "session_id": f"eq.{session_id}",
                                "memory_type": "eq.conversation_message",
                                "select": "content,metadata,created_at",
                                "order": "created_at.asc",
                                "limit": "100",
                            },
                        )
                        response.raise_for_status()
                        rows = response.json()
                        if isinstance(rows, list):
                            self.conversations[conversation_id] = [
                                {"role": (row.get("metadata") or {}).get("role", "user"), "content": row.get("content", "")}
                                for row in rows
                            ]
                except Exception:
                    pass
        return list(self.conversations.get(conversation_id, []))

    async def get_session_id(self, conversation_id: str) -> str | None:
        return await self._session_id(conversation_id)
