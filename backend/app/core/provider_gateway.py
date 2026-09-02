from __future__ import annotations

import os
from typing import Any, Protocol

import httpx


class AIProvider(Protocol):
    name: str
    priority: int

    async def health(self) -> bool:
        ...

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        ...


class OpenAICompatibleProvider:
    def __init__(self, name: str, endpoint: str, model: str, api_key: str, priority: int, free_only: bool = True) -> None:
        self.name = name
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key.strip()
        self.priority = priority
        self.free_only = free_only

    async def health(self) -> bool:
        return bool(self.api_key or self.endpoint.startswith("http://127.0.0.1") or self.endpoint.startswith("http://localhost"))

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        if not await self.health():
            raise RuntimeError("provider_not_configured")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": int(os.getenv("AI_MAX_OUTPUT_TOKENS", "1200")),
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=float(os.getenv("AI_REQUEST_TIMEOUT", "45"))) as client:
            response = await client.post(f"{self.endpoint}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        if not choices or not choices[0].get("message", {}).get("content"):
            raise RuntimeError("empty_response")
        return str(choices[0]["message"]["content"]).strip()


class CloudflareAIProvider:
    def __init__(self, model: str, account_id: str, api_token: str, priority: int) -> None:
        self.name = "cloudflare-free"
        self.model = model
        self.account_id = account_id.strip()
        self.api_token = api_token.strip()
        self.priority = priority

    async def health(self) -> bool:
        return bool(self.account_id and self.api_token)

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        if not await self.health():
            raise RuntimeError("provider_not_configured")
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{self.model}"
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=float(os.getenv("AI_REQUEST_TIMEOUT", "45"))) as client:
            response = await client.post(url, headers=headers, json={"messages": messages, "prompt": prompt})
            response.raise_for_status()
            data = response.json()
        result = data.get("result") or {}
        return str(result.get("response") or result.get("text") or "").strip()


class ProviderGateway:
    """Free-first provider council. Paid providers are blocked by configuration."""

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._register_from_environment()

    def register(self, provider: AIProvider) -> None:
        self._providers[provider.name] = provider

    def _free_only(self) -> bool:
        return os.getenv("BITEY_COST_MODE", "free_only").lower() == "free_only"

    def _register_from_environment(self) -> None:
        free_only = self._free_only()

        # Gemma 4 12B is an open Apache-2.0 model. Bitey supports it as a
        # local OpenAI-compatible provider (for example llama.cpp, LM Studio,
        # Ollama-compatible gateways or LiteRT-LM). No hosted paid service is
        # assumed and no Google Gemini API is required for this path.
        if os.getenv("GEMMA_4_12B_ENABLED", "false").lower() == "true":
            gemma_endpoint = os.getenv("GEMMA_4_12B_ENDPOINT", "http://127.0.0.1:50305/v1")
            gemma_model = os.getenv("GEMMA_4_12B_MODEL", "google/gemma-4-12B-it")
            self.register(OpenAICompatibleProvider(
                "gemma-4-12b-local",
                gemma_endpoint,
                gemma_model,
                os.getenv("GEMMA_4_12B_API_KEY", ""),
                int(os.getenv("GEMMA_4_12B_PRIORITY", "3")),
                free_only=True,
            ))

        # Groq is permitted only when the account is intentionally configured for its free allowance.
        if os.getenv("GROQ_ENABLED", "true").lower() != "false" and os.getenv("GROQ_API_KEY") and os.getenv("GROQ_ALLOW_FREE", "true").lower() == "true":
            self.register(OpenAICompatibleProvider(
                "groq", "https://api.groq.com/openai/v1",
                os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), os.getenv("GROQ_API_KEY", ""),
                int(os.getenv("GROQ_PRIORITY", "5")), free_only=free_only,
            ))

        # OpenRouter is accepted only for explicitly free-tagged models in free_only mode.
        if os.getenv("OPENROUTER_ENABLED", "false").lower() != "false" and os.getenv("OPENROUTER_API_KEY"):
            qwen = os.getenv("OPENROUTER_QWEN_MODEL", "qwen/qwen3-4b:free")
            deepseek = os.getenv("OPENROUTER_DEEPSEEK_MODEL", "deepseek/deepseek-chat-v3-0324:free")
            if not free_only or qwen.endswith(":free"):
                self.register(OpenAICompatibleProvider("qwen-free", "https://openrouter.ai/api/v1", qwen, os.getenv("OPENROUTER_API_KEY", ""), int(os.getenv("QWEN_PRIORITY", "10"))))
            if os.getenv("DEEPSEEK_ENABLED", "true").lower() != "false" and (not free_only or deepseek.endswith(":free")):
                self.register(OpenAICompatibleProvider("deepseek-free", "https://openrouter.ai/api/v1", deepseek, os.getenv("OPENROUTER_API_KEY", ""), int(os.getenv("DEEPSEEK_PRIORITY", "15"))))

        if not free_only and os.getenv("CLOUDFLARE_AI_ENABLED", "true").lower() != "false":
            account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
            token = os.getenv("CLOUDFLARE_API_TOKEN", "")
            if account_id and token:
                self.register(OpenAICompatibleProvider("cloudflare-free", "https://api.cloudflare.com/client/v4", os.getenv("CLOUDFLARE_AI_MODEL", "@cf/qwen/qwen3-0.6b"), token, int(os.getenv("CLOUDFLARE_PRIORITY", "20"))))

    def available(self) -> list[str]:
        return [p.name for p in sorted(self._providers.values(), key=lambda p: p.priority)]

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        if not self._providers:
            return "Bitey IA está en modo sin costo y no tiene un proveedor gratuito disponible en este momento."

        errors: list[str] = []
        max_providers = max(1, int(os.getenv("AI_COUNCIL_MAX_PROVIDERS", "2")))
        for provider in sorted(self._providers.values(), key=lambda p: p.priority)[:max_providers]:
            try:
                if await provider.health():
                    answer = await provider.generate(messages=messages, context=context)
                    if answer:
                        return answer
            except Exception as exc:
                errors.append(f"{provider.name}:{type(exc).__name__}")

        if errors:
            return "El proveedor gratuito no pudo completar esta consulta ahora. La conversación se conserva para continuar."
        return "Bitey IA no tiene un proveedor gratuito disponible en este momento."
