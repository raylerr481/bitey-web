"""Component ownership and zero-cost policy for Bitey IA Web.

Bitey owns the cognitive decisions. Third-party software is infrastructure only:
open-source components are allowed as required dependencies, while external
providers are optional and must never become a paid or vendor-locked path.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ComponentClass(str, Enum):
    OWNED = "owned"
    OPEN_SOURCE = "open_source"
    OPTIONAL_FREE_PROVIDER = "optional_free_provider"


@dataclass(frozen=True)
class ComponentPolicy:
    name: str
    component_class: ComponentClass
    mandatory: bool = True
    paid_dependency: bool = False
    vendor_lock_in: bool = False

    def allowed(self) -> bool:
        if self.paid_dependency:
            return False
        if self.mandatory and self.component_class == ComponentClass.OPTIONAL_FREE_PROVIDER:
            return False
        return not self.vendor_lock_in


# Runtime architecture manifest. Keep this explicit: adding a component to the
# execution path requires declaring its ownership class and cost constraints.
CORE_COMPONENTS = (
    ComponentPolicy("bitey-cognitive-core", ComponentClass.OWNED),
    ComponentPolicy("bitey-workspace-api", ComponentClass.OWNED),
    ComponentPolicy("bitey-task-runtime", ComponentClass.OWNED),
    ComponentPolicy("bitey-artifact-pipeline", ComponentClass.OWNED),
    ComponentPolicy("bitey-tool-registry", ComponentClass.OWNED),
    ComponentPolicy("bitey-evaluator", ComponentClass.OWNED),
    ComponentPolicy("bitey-memory-contract", ComponentClass.OWNED),
    ComponentPolicy("python", ComponentClass.OPEN_SOURCE),
    ComponentPolicy("fastapi", ComponentClass.OPEN_SOURCE),
    ComponentPolicy("pydantic", ComponentClass.OPEN_SOURCE),
    ComponentPolicy("httpx", ComponentClass.OPEN_SOURCE),
    ComponentPolicy("pytest", ComponentClass.OPEN_SOURCE),
    # Open-source/local accelerators remain non-authoritative.
    ComponentPolicy("qdrant", ComponentClass.OPEN_SOURCE, mandatory=False),
    ComponentPolicy("ollama", ComponentClass.OPEN_SOURCE, mandatory=False),
    # These are replaceable routes, never core dependencies.
    ComponentPolicy("openrouter-free-route", ComponentClass.OPTIONAL_FREE_PROVIDER, mandatory=False),
    ComponentPolicy("duckduckgo-search", ComponentClass.OPTIONAL_FREE_PROVIDER, mandatory=False),
    ComponentPolicy("open-meteo", ComponentClass.OPTIONAL_FREE_PROVIDER, mandatory=False),
)


def validate_core_components() -> None:
    """Fail closed if any declared component violates the zero-cost policy."""
    rejected = [component.name for component in CORE_COMPONENTS if not component.allowed()]
    if rejected:
        raise RuntimeError(
            "Bitey component policy rejected dependencies: " + ", ".join(rejected)
        )


def component_manifest() -> list[dict[str, object]]:
    """Return a safe, read-only architecture manifest for diagnostics/UI."""
    return [
        {
            "name": component.name,
            "class": component.component_class.value,
            "mandatory": component.mandatory,
            "paid_dependency": component.paid_dependency,
            "vendor_lock_in": component.vendor_lock_in,
            "allowed": component.allowed(),
        }
        for component in CORE_COMPONENTS
    ]
