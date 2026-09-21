from unittest.mock import patch

import pytest

from app.core.tool_orchestrator import ToolOrchestrator


@pytest.mark.asyncio
async def test_search_snippets_are_not_promoted_to_evidence():
    orchestrator = ToolOrchestrator()
    discovery = {
        "ok": True,
        "results": [
            {
                "url": "https://example.com/article",
                "title": "Discovery result",
                "snippet": "This is only a search-engine snippet.",
            }
        ],
    }
    with patch("app.core.tool_orchestrator.general_search", return_value=discovery):
        result = await orchestrator._search("qué es el mercado")
    assert result["verified_evidence_count"] == 0
    assert result["evidence"] == ""
    assert "This is only a search-engine snippet." not in result["evidence"]


@pytest.mark.asyncio
async def test_fetched_page_content_is_promoted_to_evidence():
    orchestrator = ToolOrchestrator()
    discovery = {
        "ok": True,
        "results": [
            {
                "url": "https://example.com/article",
                "title": "Verified result",
                "snippet": "Discovery snippet.",
            }
        ],
    }

    def fake_fetch(url, max_bytes):
        return {"ok": True, "content": "Verified page content " * 20}

    with patch("app.core.tool_orchestrator.general_search", return_value=discovery), patch(
        "app.core.search_gateway.safe_fetch", side_effect=fake_fetch
    ):
        result = await orchestrator._search("qué es el mercado")
    assert result["verified_evidence_count"] == 1
    assert "Verified page content" in result["evidence"]
    assert "Discovery snippet." not in result["evidence"]
