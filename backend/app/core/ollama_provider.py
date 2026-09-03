from __future__ import annotations

import os
from typing import Any

import httpx


class OllamaProvider:
    """Local Ollama model pool for Bitey IA.

    Ollama models are inference workers. Bitey remains responsible for cognition,
    memory, planning, evaluation, routing and recovery.
    """

    name = "ollama-local"
    priority = 1
    free_only = True

    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "").strip()
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", os.getenv("AI_REQUEST_TIMEOUT", "45")))
        self.last_model = ""

    async def _tags(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
        models = data.get("models") or []
        return [item for item in models if isinstance(item, dict) and item.get("name")]

    async def health(self) -> bool:
        try:
            return bool(await self._tags())
        except Exception:
            return False

    async def models(self) -> list[str]:
        return [str(item["name"]) for item in await self._tags()]

    async def _model_pool(self) -> list[str]:
        installed = await self.models()
        if not installed:
            raise RuntimeError("ollama_no_models")
        preferred: list[str] = []
        if self.model:
            preferred.append(self.model)
        configured = os.getenv("OLLAMA_FALLBACK_MODELS", "qwen3:4b,llama3.2:3b,gemma3:4b").split(",")
        preferred.extend(item.strip() for item in configured if item.strip())
        ordered: list[str] = []
        for candidate in preferred + installed:
            if candidate in installed and candidate not in ordered:
                ordered.append(candidate)
        return ordered

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        pool = await self._model_pool()
        last_error: Exception | None = None
        for model in pool:
            try:
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
                self.last_model = model
                context["ollama_model"] = model
                return content
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"ollama_model_pool_exhausted:{type(last_error).__name__ if last_error else 'unknown'}")
