import pytest

from app.core.provider_gateway import CloudflareAIProvider


@pytest.mark.asyncio
async def test_cloudflare_free_provider_accepts_documented_free_model():
    provider = CloudflareAIProvider(
        "@cf/zai-org/glm-4.7-flash",
        "account",
        "token",
        40,
        True,
    )
    assert provider.free_only is True
    assert await provider.health() is True


@pytest.mark.asyncio
async def test_cloudflare_free_provider_rejects_non_allowlisted_model():
    provider = CloudflareAIProvider(
        "@cf/some/paid-model",
        "account",
        "token",
        40,
        True,
    )
    assert await provider.health() is False
