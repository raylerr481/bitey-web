"""Governed tool-definition factory for Bitey IA Web.

The factory creates capability specifications, not unrestricted executable
code. A future execution layer can bind validated specifications to
sandboxed/deterministic implementations.
"""

from dataclasses import dataclass, field
from typing import Any, Callable


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
    """Create and validate tool blueprints before registry activation."""

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

    def get(self, name: str) -> ToolBlueprint | None:
        return self._blueprints.get(name)

    def available(self) -> list[str]:
        return sorted(self._blueprints)

    @staticmethod
    def _validate(blueprint: ToolBlueprint) -> None:
        if not blueprint.name.strip():
            raise ValueError("Tool name is required")
        if not blueprint.description.strip():
            raise ValueError("Tool description is required")
        if not isinstance(blueprint.input_schema, dict) or not isinstance(blueprint.output_schema, dict):
            raise TypeError("Tool schemas must be dictionaries")
        if blueprint.cost_class not in {"free", "unknown"}:
            raise PermissionError("Tool Factory rejects paid tool definitions in the free profile")
        if blueprint.timeout_seconds <= 0 or blueprint.timeout_seconds > 300:
            raise ValueError("Tool timeout must be between 1 and 300 seconds")
