from typing import Any, Protocol


class AIProvider(Protocol):
    name: str

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        ...


class ProviderGateway:
    """Neutral gateway for external AI models.

    No provider credentials or vendor SDKs belong in the supracerebro core.
    """

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}

    def register(self, provider: AIProvider) -> None:
        self._providers[provider.name] = provider

    def available(self) -> list[str]:
        return sorted(self._providers)

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        if not self._providers:
            return "Bitey IA: el supracerebro está activo, pero todavía no hay un proveedor de IA configurado."
        provider = next(iter(self._providers.values()))
        return await provider.generate(messages=messages, context=context)
