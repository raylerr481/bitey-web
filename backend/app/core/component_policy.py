"""Component ownership and zero-cost policy for Bitey IA Web.

The cognitive core remains Bitey-owned. Third-party software is permitted only
as replaceable infrastructure when it is open-source/free to use and does not
create a mandatory paid dependency.
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
        """A component is admissible only when it cannot force paid usage."""
        if self.paid_dependency:
            return False
        if self.mandatory and self.component_class == ComponentClass.OPTIONAL_FREE_PROVIDER:
            return False
        return not self.vendor_lock_in


# Canonical baseline for the current architecture. Keep this registry small and
# explicit so a future dependency cannot silently become a required service.
CORE_COMPONENTS = (
    ComponentPolicy("bitey-cognitive-core", ComponentClass.OWNED),
    ComponentPolicy("bitey-workspace-api", ComponentClass.OWNED),
    ComponentPolicy("bitey-tool-registry", ComponentClass.OWNED),
    ComponentPolicy("bitey-evaluator", ComponentClass.OWNED),
    ComponentPolicy("python", ComponentClass.OPEN_SOURCE),
    ComponentPolicy("fastapi", ComponentClass.OPEN_SOURCE),
    ComponentPolicy("pydantic", ComponentClass.OPEN_SOURCE),
    ComponentPolicy("httpx", ComponentClass.OPEN_SOURCE),
    ComponentPolicy("pytest", ComponentClass.OPEN_SOURCE),
)


def validate_core_components() -> None:
    """Fail closed if a mandatory component violates Bitey's zero-cost rule."""
    rejected = [component.name for component in CORE_COMPONENTS if not component.allowed()]
    if rejected:
        raise RuntimeError(
            "Bitey component policy rejected mandatory dependencies: " + ", ".join(rejected)
        )
