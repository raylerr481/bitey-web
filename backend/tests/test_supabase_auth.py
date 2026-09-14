from __future__ import annotations

import pytest

from app.core import supabase_auth


@pytest.mark.asyncio
async def test_missing_token_is_rejected() -> None:
    with pytest.raises(supabase_auth.SupabaseAuthError, match="missing_bearer_token"):
        await supabase_auth.resolve_supabase_user("")


@pytest.mark.asyncio
async def test_auth_endpoint_identity_is_authoritative(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"id": "user-123", "email": "user@example.com", "role": "authenticated"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers):
            assert url == "https://example.supabase.co/auth/v1/user"
            assert headers["apikey"] == "public-key"
            assert headers["Authorization"] == "Bearer token-123"
            return FakeResponse()

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-key")
    monkeypatch.setattr(supabase_auth.httpx, "AsyncClient", lambda timeout: FakeClient())

    user = await supabase_auth.resolve_supabase_user("token-123")
    assert user.user_id == "user-123"
    assert user.email == "user@example.com"
    assert user.role == "authenticated"


@pytest.mark.asyncio
async def test_invalid_auth_response_is_rejected(monkeypatch) -> None:
    class FakeResponse:
        status_code = 401

        def json(self):
            return {"error": "invalid_token"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers):
            return FakeResponse()

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-key")
    monkeypatch.setattr(supabase_auth.httpx, "AsyncClient", lambda timeout: FakeClient())

    with pytest.raises(supabase_auth.SupabaseAuthError, match="invalid_or_expired_token"):
        await supabase_auth.resolve_supabase_user("expired")
