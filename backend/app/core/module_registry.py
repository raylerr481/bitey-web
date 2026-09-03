"""Domain-neutral registry for Bitey ecosystem capability modules.

A module can be functionally owned by Bitey IA while remaining technically
independently deployed. The registry describes contracts and capabilities; it
does not import specialized application code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    description: str
    endpoint: str | None = None
    capabilities: tuple[str, ...] = ()
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def integration_type(self) -> str:
        return str(self.metadata.get("integration_type", "external_specialized"))

    @property
    def role(self) -> str:
        return str(self.metadata.get("role", "specialized_module"))


class ModuleRegistry:
    """Runtime capability registry with explicit ownership semantics."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleSpec] = {}

    def register(self, module: ModuleSpec) -> None:
        self._modules[module.name] = module

    def available(self) -> list[dict[str, Any]]:
        return [
            {
                "name": m.name,
                "description": m.description,
                "endpoint": m.endpoint,
                "capabilities": list(m.capabilities),
                "enabled": m.enabled,
                "configured": bool(m.endpoint),
                "integration_type": m.integration_type,
                "role": m.role,
                "metadata": dict(m.metadata),
            }
            for m in sorted(self._modules.values(), key=lambda item: item.name)
            if m.enabled
        ]

    def find_for(self, capability: str) -> list[ModuleSpec]:
        key = capability.strip().lower()
        return [
            m for m in self._modules.values()
            if m.enabled and key in {c.lower() for c in m.capabilities}
        ]

    def resolve_for_domain(self, domain: str) -> list[ModuleSpec]:
        """Resolve the specialized capability owner for a cognitive domain."""
        domain = domain.strip().lower()
        aliases = {
            "trading": ("trading", "market_intelligence", "strategy", "risk"),
            "support": ("business_support", "crm", "tickets", "customer_context"),
        }
        capabilities = aliases.get(domain, (domain,))
        seen: set[str] = set()
        result: list[ModuleSpec] = []
        for capability in capabilities:
            for module in self.find_for(capability):
                if module.name not in seen:
                    seen.add(module.name)
                    result.append(module)
        return result

    def names(self) -> list[str]:
        return [m.name for m in self._modules.values() if m.enabled]
