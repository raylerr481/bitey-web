from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from .execution_context import ExecutionContext, server_execution_context


_UNTRUSTED_SCOPE_KEYS = {
    "tenant_id",
    "user_id",
    "company_id",
    "enterprise_company_id",
    "enterprise",
}


@dataclass
class MemoryStore:
    """General Bitey conversation memory with explicit execution-scope metadata."""

    conversations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    @property
    def persistent(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @staticmethod
    def _metadata(
        metadata: dict[str, Any] | None = None,
        execution_context: ExecutionContext | None = None,
    ) -> dict[str, Any]:
        # Never persist request-controlled identity or tenant selectors as authority.
        clean = {
            key: value
            for key, value in (metadata or {}).items()
            if key not in _UNTRUSTED_SCOPE_KEYS
        }
        result = {**clean, "owner": "bitey_ia"}
        if execution_context is None:
            result.setdefault("memory_scope", "general")
            return result
        result.update({
            "memory_scope": execution_context.memory_scope,
            "execution_scope": execution_context.as_dict(),
        })
        return result

    @staticmethod
    def _scope(conversation_id: str, execution_context: ExecutionContext | None) -> ExecutionContext:
        return execution_context or server_execution_context(conversation_id)

    async def create_conversation(
        self,
        conversation_id: str,
        metadata: dict[str, Any] | None = None,
        execution_context: ExecutionContext | None = None,
    ) -> None:
        scope = self._scope(conversation_id, execution_context)
        self.conversations.setdefault(conversation_id, [])
        if not self.persistent:
            return
        payload = {
            "id": conversation_id,
            "metadata": self._metadata(metadata, scope),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.supabase_url}/rest/v1/conversations",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()

    async def append(
        self,
        conversation_id: str,
        message: dict[str, Any],
        execution_context: ExecutionContext | None = None,
    ) -> None:
        scope = self._scope(conversation_id, execution_context)
        self.conversations.setdefault(conversation_id, []).append(message)
        if not self.persistent:
            return
        payload = {
            "conversation_id": conversation_id,
            "role": message["role"],
            "content": message["content"],
            "metadata": self._metadata(message.get("metadata"), scope),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.supabase_url}/rest/v1/messages",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()

    async def history(
        self,
        conversation_id: str,
        execution_context: ExecutionContext | None = None,
    ) -> list[dict[str, Any]]:
        scope = self._scope(conversation_id, execution_context)
        if self.persistent:
            async with httpx.AsyncClient(timeout=10) as client:
                params: dict[str, str] = {
                    "conversation_id": f"eq.{conversation_id}",
                    "select": "role,content,created_at,metadata",
                    "order": "created_at.asc",
                    "metadata->>memory_scope": f"eq.{scope.memory_scope}",
                }
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/messages",
                    headers=self._headers(),
                    params=params,
                )
                response.raise_for_status()
                rows = response.json()
                self.conversations[conversation_id] = [
                    {"role": row["role"], "content": row["content"]}
                    for row in rows
                ]
        return list(self.conversations.get(conversation_id, []))

    async def conversation_metadata(self, conversation_id: str) -> dict[str, Any] | None:
        if not self.persistent:
            return None
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{self.supabase_url}/rest/v1/conversations",
                headers=self._headers(),
                params={
                    "id": f"eq.{conversation_id}",
                    "select": "metadata",
                    "limit": "1",
                },
            )
            response.raise_for_status()
            rows = response.json()
            if not rows:
                return None
            metadata = rows[0].get("metadata")
            return metadata if isinstance(metadata, dict) else {}

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
