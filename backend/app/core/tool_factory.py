"""Governed Tool Factory for Bitey IA Web.

Bitey may design new capabilities from a detected need, but it cannot turn
model-generated text into unrestricted executable code. Every proposed tool is
validated as a capability contract and must pass authorization before it can
produce side effects.
"""
from dataclasses import dataclass, field
from typing import Any, Callable
import re


@dataclass(frozen=True)
class ToolBlueprint:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permissions: tuple[str, ...] = ()
    cost_class: str = "free"
    side_effects: tuple[str, ...] = ()
    timeout_seconds: int = 15
    network_access: bool = False
    implementation: Callable[..., Any] | None = field(default=None, repr=False, compare=False)

    @property
    def requires_authorization(self) -> bool:
        return bool(self.permissions or self.side_effects or self.network_access)


class ToolFactory:
    """Design, validate and register bounded tool blueprints."""

    NAME_RE = re.compile(r"^[a-z][a-z0-9_\-]{1,63}$")

    def __init__(self) -> None:
        self._blueprints: dict[str, ToolBlueprint] = {}

    def propose(self, blueprint: ToolBlueprint) -> ToolBlueprint:
        self._validate(blueprint)
        return blueprint

    def register(self, blueprint: ToolBlueprint, *, authorized: bool = False) -> ToolBlueprint:
        self._validate(blueprint)
        if blueprint.requires_authorization and not authorized:
            raise PermissionError(f"Tool requires authorization: {blueprint.name}")
        self._blueprints[blueprint.name] = blueprint
        return blueprint

    def propose_from_need(self, need: str) -> ToolBlueprint | None:
        """Create a safe specification from a natural-language capability need.

        This is deliberately specification-only: it never generates or executes
        arbitrary Python/shell code. Implementation binding happens separately.
        """
        text = need.strip()
        if not text:
            return None
        normalized = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        name = "generated_" + normalized[:50]
        name = re.sub(r"_+", "_", name)
        blueprint = ToolBlueprint(
            name=name,
            description=f"Capability proposed by Bitey from need: {text[:300]}",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            cost_class="free",
            timeout_seconds=15,
            network_access=False,
        )
        return self.propose(blueprint)

    def get(self, name: str) -> ToolBlueprint | None:
        return self._blueprints.get(name)

    def available(self) -> list[str]:
        return sorted(self._blueprints)

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item.name,
                "description": item.description,
                "permissions": list(item.permissions),
                "cost_class": item.cost_class,
                "side_effects": list(item.side_effects),
                "network_access": item.network_access,
                "requires_authorization": item.requires_authorization,
            }
            for item in self._blueprints.values()
        ]

    @classmethod
    def _validate(cls, blueprint: ToolBlueprint) -> None:
        if not cls.NAME_RE.match(blueprint.name.strip()):
            raise ValueError("Tool name must use 2-64 lowercase alphanumeric/underscore/hyphen characters")
        if not blueprint.description.strip():
            raise ValueError("Tool description is required")
        if not isinstance(blueprint.input_schema, dict) or not isinstance(blueprint.output_schema, dict):
            raise TypeError("Tool schemas must be dictionaries")
        if blueprint.cost_class != "free":
            raise PermissionError("Tool Factory rejects non-free tool definitions")
        if blueprint.timeout_seconds <= 0 or blueprint.timeout_seconds > 300:
            raise ValueError("Tool timeout must be between 1 and 300 seconds")
        if not isinstance(blueprint.permissions, tuple) or not isinstance(blueprint.side_effects, tuple):
            raise TypeError("Permissions and side effects must be tuples")
