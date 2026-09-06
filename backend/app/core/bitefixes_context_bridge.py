from __future__ import annotations

import os
from typing import Any

import httpx


class BiteFixesContextBridge:
    """Read-only, on-demand bridge from general Bitey to BiteFixes context."""

    def __init__(self) -> None:
        self.base_url = os.getenv("BITEFIXES_BACKEND_URL", "https://bitefixes-backend.onrender.com").rstrip("/")
        self.api_key = os.getenv("BITEY_CONTEXT_API_KEY", "").strip()
        self.timeout = max(0.5, float(os.getenv("BITEY_CONTEXT_BRIDGE_TIMEOUT", "2")))

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def company_sync(self, company_id: str) -> dict[str, Any] | None:
        """Synchronous bridge used during context assembly for the request path."""
        if not self.configured or not company_id:
            return None
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/bitey-context/company/{company_id}",
                    headers={"X-Bitey-Context-Key": self.api_key},
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else None
        except Exception:
            return None

    async def company(self, company_id: str) -> dict[str, Any] | None:
        if not self.configured or not company_id:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/bitey-context/company/{company_id}",
                    headers={"X-Bitey-Context-Key": self.api_key},
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else None
        except Exception:
            return None
