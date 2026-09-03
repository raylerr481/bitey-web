"""Economic policy for Bitey IA Web.

This module is deliberately independent from any model provider.  It provides
one small invariant: FREE_ONLY may only admit routes explicitly verified as
free.  Unknown pricing fails closed.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FreeRoute:
    provider: str
    model: str
    verified_free: bool
    local: bool = False


class FreePolicy:
    """Enforce Bitey's no-paid-fallback boundary."""

    mode = "free_only"
    hard_stop = True

    @classmethod
    def allowed(cls, route: FreeRoute) -> bool:
        # Local inference has no hosted model billing boundary here.
        if route.local:
            return True
        return route.verified_free

    @classmethod
    def choose(cls, routes: list[FreeRoute]) -> list[FreeRoute]:
        """Return only eligible routes, preserving caller ranking."""
        return [route for route in routes if cls.allowed(route)]

    @classmethod
    def assert_free(cls, route: FreeRoute) -> None:
        if not cls.allowed(route):
            raise PermissionError(
                "Bitey FREE_ONLY policy rejected an unverified or paid route"
            )
