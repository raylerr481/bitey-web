from __future__ import annotations

import os
from typing import Any

from .ollama import OllamaLanguagePlanner
from .schemas import NativePlan


class NativeLanguageModelAdapter:
    """Selects a local/free planner and fails closed to the deterministic planner."""

    def __init__(self) -> None:
        self.enabled = os.getenv("BITEY_NATIVE_LANGUAGE_PLANNER", "true").lower() == "true"
        self.provider = os.getenv("BITEY_NATIVE_LANGUAGE_PROVIDER", "ollama").lower()
        self.ollama = OllamaLanguagePlanner() if self.provider == "ollama" else None

    async def plan(self, message: str, context: dict[str, Any] | None = None) -> NativePlan | None:
        if not self.enabled or self.ollama is None:
            return None
        return await self.ollama.plan(message, context)

    async def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "provider": self.provider, "available": False}
        available = await self.ollama.health() if self.ollama else False
        return {"enabled": True, "provider": self.provider, "model": getattr(self.ollama, "model", None), "available": available, "mode": "local_free_fail_closed"}
