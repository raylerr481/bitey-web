from __future__ import annotations

import os
from typing import Any, Protocol

import httpx


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
            return
        self._providers[provider.name] = provider

    def _free_only(self) -> bool:
        return os.getenv("BITEY_COST_MODE", "free_only").lower() == "free_only"

    def _hard_stop(self) -> bool:
        return os.getenv("BITEY_FREE_ONLY_HARD_STOP", "true").lower() == "true"

    def _register_from_environment(self) -> None:
        free_only = self._free_only()

        # Gemma 4 12B: open Apache-2.0 model. Bitey can use it locally through
        # any OpenAI-compatible server. This path requires no Gemini API.
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

        # Remote providers are admitted only when the deployment explicitly
        # confirms that the selected model is free under the active plan.
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

        # Static OpenRouter entries are retained for deterministic operation,
        # but new free models are discovered automatically in generate().
        if os.getenv("OPENROUTER_ENABLED", "false").lower() != "false" and os.getenv("OPENROUTER_API_KEY"):
            qwen = os.getenv("OPENROUTER_QWEN_MODEL", "qwen/qwen3-4b:free")
            deepseek = os.getenv("OPENROUTER_DEEPSEEK_MODEL", "deepseek/deepseek-chat-v3-0324:free")
            if self._is_free_model_id(qwen):
                self.register(OpenAICompatibleProvider("qwen-free", "https://openrouter.ai/api/v1", qwen, os.getenv("OPENROUTER_API_KEY", ""), int(os.getenv("QWEN_PRIORITY", "10")), free_only=True))
            if os.getenv("DEEPSEEK_ENABLED", "true").lower() != "false" and self._is_free_model_id(deepseek):
                self.register(OpenAICompatibleProvider("deepseek-free", "https://openrouter.ai/api/v1", deepseek, os.getenv("OPENROUTER_API_KEY", ""), int(os.getenv("DEEPSEEK_PRIORITY", "15")), free_only=True))

        # Never register this provider while free_only is active. Cloudflare
        # pricing depends on the account/plan, so it cannot be treated as a
        # guaranteed zero-cost provider by Bitey's hard guard.
        if not free_only and os.getenv("CLOUDFLARE_AI_ENABLED", "true").lower() != "false":
            account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
            token = os.getenv("CLOUDFLARE_API_TOKEN", "")
            if account_id and token:
                self.register(CloudflareAIProvider(os.getenv("CLOUDFLARE_AI_MODEL", "@cf/qwen/qwen3-0.6b"), account_id, token, int(os.getenv("CLOUDFLARE_PRIORITY", "20"))))

    @staticmethod
    def _is_free_model_id(model_id: str) -> bool:
        return model_id == "openrouter/free" or model_id.endswith(":free")

    async def _discover_openrouter_free_models(self) -> None:
        """Discover currently zero-priced OpenRouter free variants without hardcoding them."""
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
        except Exception:
            # Discovery is opportunistic. Existing explicitly configured free
            # providers remain available; failure never opens a paid fallback.
            self._openrouter_catalog_loaded = True

    def available(self) -> list[str]:
        return [p.name for p in sorted(self._providers.values(), key=lambda p: p.priority)]

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        await self._discover_openrouter_free_models()

        providers = [p for p in self._providers.values() if not self._free_only() or p.free_only]
        if not providers:
            if self._hard_stop() and self._free_only():
                return "billing_risk_blocked: Bitey está en FREE_ONLY y no dispone de un proveedor gratuito verificado. No se utilizará ningún proveedor de pago."
            return "Bitey IA no tiene un proveedor disponible en este momento."

        errors: list[str] = []
        max_providers = max(1, int(os.getenv("AI_COUNCIL_MAX_PROVIDERS", "2")))
        for provider in sorted(providers, key=lambda p: p.priority)[:max_providers]:
            try:
                if await provider.health():
                    answer = await provider.generate(messages=messages, context=context)
                    if answer:
                        return answer
            except Exception as exc:
                errors.append(f"{provider.name}:{type(exc).__name__}")

        if errors:
            return "El proveedor gratuito no pudo completar esta consulta ahora. Bitey mantiene el modo FREE_ONLY y no hará fallback a servicios de pago."
        return "Bitey IA no tiene un proveedor gratuito disponible en este momento."
