from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identity returned by Supabase Auth after server-side token validation."""

    user_id: str
    email: str | None = None
    role: str | None = None


class SupabaseAuthError(RuntimeError):
    """Raised when a bearer token cannot be validated by Supabase Auth."""


def _supabase_auth_config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not url or not key:
        raise SupabaseAuthError("supabase_auth_not_configured")
    return url, key


async def resolve_supabase_user(access_token: str) -> AuthenticatedUser:
    """Validate an access token against Supabase Auth's user endpoint.

    The backend never trusts user_id, tenant_id, or module values supplied by
    the browser. Supabase Auth is the identity authority for the bearer token.
    """
    token = str(access_token or "").strip()
    if not token:
        raise SupabaseAuthError("missing_bearer_token")

    base_url, publishable_key = _supabase_auth_config()
    headers = {
        "apikey": publishable_key,
        "Authorization": f"Bearer {token}",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"{base_url}/auth/v1/user", headers=headers)
    except httpx.HTTPError as exc:
        raise SupabaseAuthError("supabase_auth_unreachable") from exc

    if response.status_code != 200:
        raise SupabaseAuthError("invalid_or_expired_token")

    try:
        data = response.json()
    except ValueError as exc:
        raise SupabaseAuthError("invalid_auth_response") from exc

    user_id = str(data.get("id") or "").strip()
    if not user_id:
        raise SupabaseAuthError("auth_user_id_missing")

    return AuthenticatedUser(
        user_id=user_id,
        email=str(data.get("email") or "").strip() or None,
        role=str(data.get("role") or "").strip() or None,
    )
