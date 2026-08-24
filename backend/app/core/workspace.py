from __future__ import annotations

import os
from typing import Any

import httpx


class WorkspaceStore:
    """Persistent projects/files/feedback for the independent Supracerebro DB."""

    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    @property
    def persistent(self) -> bool:
        return bool(self.url and self.key)

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def _request(self, method: str, table: str, **kwargs: Any) -> list[dict[str, Any]]:
        if not self.persistent:
            return []
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(
                method,
                f"{self.url}/rest/v1/{table}",
                headers=self._headers(),
                **kwargs,
            )
            response.raise_for_status()
            return response.json() if response.content else []

    async def create_project(self, name: str, description: str = "", instructions: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        rows = await self._request("POST", "projects", json={
            "name": name,
            "description": description,
            "instructions": instructions,
            "metadata": metadata or {},
        })
        return rows[0] if rows else {"name": name, "description": description, "instructions": instructions}

    async def list_projects(self) -> list[dict[str, Any]]:
        return await self._request("GET", "projects", params={"select": "*", "order": "updated_at.desc"})

    async def attach_conversation(self, project_id: str, conversation_id: str) -> None:
        await self._request("POST", "project_conversations", json={"project_id": project_id, "conversation_id": conversation_id})

    async def add_file_metadata(self, project_id: str, name: str, mime_type: str | None = None, size_bytes: int | None = None, extracted_text: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        rows = await self._request("POST", "project_files", json={
            "project_id": project_id,
            "name": name,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "extracted_text": extracted_text,
            "metadata": metadata or {},
        })
        return rows[0] if rows else {"project_id": project_id, "name": name}

    async def feedback(self, conversation_id: str, message_id: str | None, rating: int | None, feedback: str | None) -> None:
        payload = {"conversation_id": conversation_id, "rating": rating, "feedback": feedback}
        if message_id:
            payload["message_id"] = message_id
        await self._request("POST", "response_feedback", json=payload)
