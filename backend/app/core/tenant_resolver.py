from __future__ import annotations

import json
import os


class TenantResolutionError(RuntimeError):
    """Raised when trusted tenant configuration cannot be evaluated safely."""


def resolve_tenant_id(user_id: str) -> str | None:
    """Resolve a tenant only from server-controlled configuration.

    The browser cannot select a tenant. No email-domain, request metadata,
    query parameter, or user metadata is used as a tenant authority.
    Missing or malformed mappings fail closed by returning None.
    """
    uid = str(user_id or "").strip()
    if not uid or uid == "anonymous":
        return None

    raw = os.getenv("BITEY_USER_TENANT_MAP_JSON", "").strip()
    if not raw:
        return None

    try:
        mapping = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise TenantResolutionError("invalid_tenant_mapping") from exc

    if not isinstance(mapping, dict):
        raise TenantResolutionError("invalid_tenant_mapping")

    tenant_id = mapping.get(uid)
    if not isinstance(tenant_id, str):
        return None

    tenant_id = tenant_id.strip()
    return tenant_id or None
