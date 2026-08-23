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
    """Small dependency-free adapter for OpenAI-compatible providers."""

    def __init__(self, name: str, endpoint: str, model: str, api_key: str, priority: int) -> None:
        self.name = name
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key.strip()
        self.priority = priority

    async def health(self) -> bool:
        return bool(self.api_key)

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        if not self.api_key:
            raise RuntimeError("provider_not_configured")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": int(os.getenv("AI_MAX_OUTPUT_TOKENS", "1200")),
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=float(os.getenv("AI_REQUEST_TIMEOUT", "45"))) as client:
            response = await client.post(f"{self.endpoint}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        if not choices or not choices[0].get("message", {}).get("content"):
            raise RuntimeError("empty_response")
        return str(choices[0]["message"]["content"]).strip()


class CloudflareAIProvider:
    """Cloudflare Workers AI adapter; optional until credentials are supplied."""

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
    """Independent multi-provider gateway for Bitey IA Supracerebro.

    Mirrors the proven BiteFixes provider pattern while keeping credentials,
    memory and business context completely separate from BiteFixes Backend.
    """

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._register_from_environment()

    def register(self, provider: AIProvider) -> None:
        self._providers[provider.name] = provider

    def _register_from_environment(self) -> None:
        if os.getenv("GROQ_ENABLED", "true").lower() != "false":
            key = os.getenv("GROQ_API_KEY", "")
            if key:
                self.register(OpenAICompatibleProvider(
                    "groq", "https://api.groq.com/openai/v1",
                    os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), key,
                    int(os.getenv("GROQ_PRIORITY", "5")),
                ))

        if os.getenv("OPENROUTER_ENABLED", "false").lower() != "false":
            key = os.getenv("OPENROUTER_API_KEY", "")
            if key:
                self.register(OpenAICompatibleProvider(
                    "qwen-free", "https://openrouter.ai/api/v1",
                    os.getenv("OPENROUTER_QWEN_MODEL", "qwen/qwen3-4b:free"), key,
                    int(os.getenv("QWEN_PRIORITY", "10")),
                ))
                if os.getenv("DEEPSEEK_ENABLED", "true").lower() != "false":
                    self.register(OpenAICompatibleProvider(
                        "deepseek-free", "https://openrouter.ai/api/v1",
                        os.getenv("OPENROUTER_DEEPSEEK_MODEL", "deepseek/deepseek-chat-v3-0324:free"), key,
                        int(os.getenv("DEEPSEEK_PRIORITY", "15")),
                    ))

        if os.getenv("CLOUDFLARE_AI_ENABLED", "true").lower() != "false":
            account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
            token = os.getenv("CLOUDFLARE_API_TOKEN", "")
            if account_id and token:
                self.register(CloudflareAIProvider(
                    os.getenv("CLOUDFLARE_AI_MODEL", "@cf/qwen/qwen3-0.6b"),
                    account_id, token, int(os.getenv("CLOUDFLARE_PRIORITY", "20")),
                ))

    def available(self) -> list[str]:
        return [p.name for p in sorted(self._providers.values(), key=lambda p: p.priority)]

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        if not self._providers:
            return "Bitey IA: el supracerebro está activo, pero todavía no hay un proveedor de IA configurado."

        errors: list[str] = []
        max_providers = max(1, int(os.getenv("AI_COUNCIL_MAX_PROVIDERS", "2")))
        candidates = sorted(self._providers.values(), key=lambda p: p.priority)
        attempted = 0
        for provider in candidates:
            if attempted >= max_providers:
                break
            if not await provider.health():
                continue
            attempted += 1
            try:
                answer = await provider.generate(messages=messages, context=context)
                if answer:
                    return answer
            except Exception as exc:
                errors.append(f"{provider.name}:{type(exc).__name__}")

        # Keep provider internals out of the user-facing answer.
        if errors:
            return "La IA externa no pudo completar esta consulta en este momento. La conversación y el contexto se mantienen para continuar sin perder el aprendizaje."
        return "Bitey IA: hay proveedores registrados, pero ninguno está disponible en este momento."
