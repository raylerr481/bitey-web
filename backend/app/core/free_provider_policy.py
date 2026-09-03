from __future__ import annotations

"""Economic guardrails for external AI providers.

Bitey may use external providers only when the user explicitly allows cloud
routing and the selected provider/model is verified as free. This module is a
policy layer, not a pricing promise: providers whose free status cannot be
verified are rejected by default.
"""

import os
from typing import Any


def env_true(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default).lower()).strip().lower() == "true"


def free_only_mode() -> bool:
    return os.getenv("BITEY_COST_MODE", "free_only").strip().lower() == "free_only"


def cloud_allowed() -> bool:
    return env_true("BITEY_ALLOW_CLOUD", False)


def hard_stop() -> bool:
    return env_true("BITEY_FREE_ONLY_HARD_STOP", True)


def openrouter_model_is_free(model_id: str) -> bool:
    """Accept only OpenRouter's explicit free model marker."""
    value = str(model_id or "").strip().lower()
    return value == "openrouter/free" or value.endswith(":free")


def openrouter_pricing_is_zero(item: dict[str, Any]) -> bool:
    pricing = item.get("pricing") or {}
    return str(pricing.get("prompt", "")) in {"0", "0.0", "0.00"} and str(
        pricing.get("completion", "")
    ) in {"0", "0.0", "0.00"}


def groq_free_is_authorized() -> bool:
    """Groq has no portable pricing API we can treat as authoritative.

    Therefore Bitey requires an explicit local confirmation before using a Groq
    key in free-only mode. If the confirmation is absent, Groq is skipped.
    """
    return env_true("GROQ_FREE_ONLY_CONFIRMED", False)


def can_use_external_free_provider(provider: str, *, model: str = "") -> bool:
    if not cloud_allowed() or not free_only_mode():
        return False
    provider = provider.strip().lower()
    if provider == "openrouter":
        return openrouter_model_is_free(model)
    if provider == "groq":
        return groq_free_is_authorized()
    return False
