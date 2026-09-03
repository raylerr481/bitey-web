from __future__ import annotations

import os
from typing import Any

import httpx


class OllamaProvider:
    """Local Ollama provider for Bitey IA.

    Ollama is intentionally treated as an inference worker, not as Bitey's brain.
    Bitey keeps cognition, memory, planning, evaluation and routing in its own core.
    """

    name = "ollama-local"
    priority = 1
    free_only = True

    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "").strip()
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", os.getenv("AI_REQUEST_TIMEOUT", "45")))

    async def _tags(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
        models = data.get("models") or []
        return [item for item in models if isinstance(item, dict) and item.get("name")]

    async def health(self) -> bool:
        try:
            models = await self._tags()
            if self.model:
                return any(str(item.get("name")) == self.model for item in models)
            return bool(models)
        except Exception:
            return False

    async def _resolve_model(self) -> str:
        if self.model:
            return self.model
        models = await self._tags()
        if not models:
            raise RuntimeError("ollama_no_models")
        self.model = str(models[0]["name"])
        return self.model

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        if not await self.health():
            raise RuntimeError("ollama_unavailable")
        model = await self._resolve_model()
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        content = ((data.get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("ollama_empty_response")
        context["ollama_model"] = model
        return content

    async def models(self) -> list[str]:
        return [str(item["name"]) for item in await self._tags()]
