"""Domain-neutral registry for external Bitey ecosystem modules.

Modules are capabilities behind contracts, not imported application internals.
This keeps BiteFixes and SBT independently deployable while allowing Bitey Core
 to discover what a specialized module can do.
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


class ModuleRegistry:
    """Runtime registry; no dependency on any specialized backend."""

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
                "metadata": dict(m.metadata),
            }
            for m in sorted(self._modules.values(), key=lambda item: item.name)
            if m.enabled
        ]

    def find_for(self, capability: str) -> list[ModuleSpec]:
        key = capability.strip().lower()
        return [m for m in self._modules.values() if m.enabled and key in {c.lower() for c in m.capabilities}]

    def names(self) -> list[str]:
        return [m.name for m in self._modules.values() if m.enabled]
