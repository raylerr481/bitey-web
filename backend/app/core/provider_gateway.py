from __future__ import annotations

import logging
import os
import time
from typing import Any, Protocol

import httpx


logger = logging.getLogger("bitey.providers")


class AIProvider(Protocol):
    name: str
    priority: int
    free_only: bool

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
        payload = {"model": self.model, "messages": messages, "temperature": 0.2, "max_tokens": int(os.getenv("AI_MAX_OUTPUT_TOKENS", "1200"))}
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
        self.name = "cloudflare-paid-or-plan-dependent"
        self.model = model
        self.account_id = account_id.strip()
        self.api_token = api_token.strip()
        self.priority = priority
        self.free_only = False

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
    """Bitey's provider council with a hard no-billing boundary in free_only mode."""

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._openrouter_catalog_loaded = False
        self._register_from_environment()

    def register(self, provider: AIProvider) -> None:
        if self._free_only() and not provider.free_only:
            logger.info("provider_rejected_free_only provider=%s", provider.name)
            return
        self._providers[provider.name] = provider

    def _free_only(self) -> bool:
        return os.getenv("BITEY_COST_MODE", "free_only").lower() == "free_only"

    def _hard_stop(self) -> bool:
        return os.getenv("BITEY_FREE_ONLY_HARD_STOP", "true").lower() == "true"

    def _register_from_environment(self) -> None:
        free_only = self._free_only()

        if os.getenv("GEMMA_4_12B_ENABLED", "false").lower() == "true":
            endpoint = os.getenv("GEMMA_4_12B_ENDPOINT", "http://127.0.0.1:50305/v1")
            self.register(OpenAICompatibleProvider(
                "gemma-4-12b-local",
                endpoint,
                os.getenv("GEMMA_4_12B_MODEL", "google/gemma-4-12B-it"),
                os.getenv("GEMMA_4_12B_API_KEY", ""),
                int(os.getenv("GEMMA_4_12B_PRIORITY", "3")),
                free_only=endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost"),
            ))

        if (
            os.getenv("GROQ_ENABLED", "true").lower() != "false"
            and os.getenv("GROQ_API_KEY")
            and os.getenv("GROQ_ALLOW_FREE", "true").lower() == "true"
            and os.getenv("GROQ_FREE_ONLY_CONFIRMED", "false").lower() == "true"
        ):
            self.register(OpenAICompatibleProvider(
                "groq-free",
                "https://api.groq.com/openai/v1",
                os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                os.getenv("GROQ_API_KEY", ""),
                int(os.getenv("GROQ_PRIORITY", "5")),
                free_only=True,
            ))

        if os.getenv("OPENROUTER_ENABLED", "false").lower() != "false" and os.getenv("OPENROUTER_API_KEY"):
            qwen = os.getenv("OPENROUTER_QWEN_MODEL", "qwen/qwen3-4b:free")
            deepseek = os.getenv("OPENROUTER_DEEPSEEK_MODEL", "deepseek/deepseek-chat-v3-0324:free")
            if self._is_free_model_id(qwen):
                self.register(OpenAICompatibleProvider("qwen-free", "https://openrouter.ai/api/v1", qwen, os.getenv("OPENROUTER_API_KEY", ""), int(os.getenv("QWEN_PRIORITY", "10")), free_only=True))
            if os.getenv("DEEPSEEK_ENABLED", "true").lower() != "false" and self._is_free_model_id(deepseek):
                self.register(OpenAICompatibleProvider("deepseek-free", "https://openrouter.ai/api/v1", deepseek, os.getenv("OPENROUTER_API_KEY", ""), int(os.getenv("DEEPSEEK_PRIORITY", "15")), free_only=True))

        if not free_only and os.getenv("CLOUDFLARE_AI_ENABLED", "true").lower() != "false":
            account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
            token = os.getenv("CLOUDFLARE_API_TOKEN", "")
            if account_id and token:
                self.register(CloudflareAIProvider(os.getenv("CLOUDFLARE_AI_MODEL", "@cf/qwen/qwen3-0.6b"), account_id, token, int(os.getenv("CLOUDFLARE_PRIORITY", "20"))))

    @staticmethod
    def _is_free_model_id(model_id: str) -> bool:
        return model_id == "openrouter/free" or model_id.endswith(":free")

    async def _discover_openrouter_free_models(self) -> None:
        if self._openrouter_catalog_loaded:
            return
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key or os.getenv("OPENROUTER_ENABLED", "false").lower() == "false":
            return
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(timeout=float(os.getenv("OPENROUTER_CATALOG_TIMEOUT", "12"))) as client:
                response = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
                response.raise_for_status()
                data = response.json()
            models = data.get("data") or []
            base_priority = int(os.getenv("OPENROUTER_DISCOVERED_PRIORITY", "25"))
            for item in models:
                model_id = str(item.get("id") or "")
                pricing = item.get("pricing") or {}
                prompt_price = str(pricing.get("prompt", ""))
                completion_price = str(pricing.get("completion", ""))
                if not self._is_free_model_id(model_id):
                    continue
                if prompt_price not in {"0", "0.0", "0.00"} or completion_price not in {"0", "0.0", "0.00"}:
                    continue
                safe_name = "openrouter-free-" + model_id.replace("/", "-").replace(":", "-")
                self.register(OpenAICompatibleProvider(safe_name, "https://openrouter.ai/api/v1", model_id, api_key, base_priority, free_only=True))
                base_priority += 1
            self._openrouter_catalog_loaded = True
            logger.info("openrouter_catalog_discovered free_models=%d", len([p for p in self._providers if p.startswith("openrouter-free-")]))
        except Exception as exc:
            self._openrouter_catalog_loaded = True
            logger.warning("openrouter_catalog_discovery_failed error=%s", type(exc).__name__)

    def available(self) -> list[str]:
        return [p.name for p in sorted(self._providers.values(), key=lambda p: p.priority)]

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        await self._discover_openrouter_free_models()
        providers = [p for p in self._providers.values() if not self._free_only() or p.free_only]
        if not providers:
            logger.warning("provider_council_no_free_provider hard_stop=%s", self._hard_stop())
            if self._hard_stop() and self._free_only():
                return "Ahora mismo no puedo completar esta consulta. Inténtalo nuevamente en unos momentos."
            return "Bitey IA no tiene un proveedor disponible en este momento."

        max_providers = max(1, int(os.getenv("AI_COUNCIL_MAX_PROVIDERS", "2")))
        for attempt, provider in enumerate(sorted(providers, key=lambda p: p.priority)[:max_providers], start=1):
            started = time.perf_counter()
            try:
                healthy = await provider.health()
                if not healthy:
                    logger.warning("provider_unhealthy provider=%s attempt=%d", provider.name, attempt)
                    continue
                answer = await provider.generate(messages=messages, context=context)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                if answer:
                    logger.info("provider_selected provider=%s model=%s attempt=%d elapsed_ms=%d", provider.name, getattr(provider, "model", ""), attempt, elapsed_ms)
                    return answer
                logger.warning("provider_empty_response provider=%s attempt=%d elapsed_ms=%d", provider.name, attempt, elapsed_ms)
            except Exception as exc:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                logger.warning("provider_failed provider=%s model=%s attempt=%d elapsed_ms=%d error=%s", provider.name, getattr(provider, "model", ""), attempt, elapsed_ms, type(exc).__name__)

        logger.warning("provider_council_exhausted attempted=%d", min(len(providers), max_providers))
        return "Ahora mismo no puedo completar esta consulta. Inténtalo nuevamente en unos momentos."
