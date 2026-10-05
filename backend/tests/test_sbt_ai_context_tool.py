from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.tool_orchestrator import ToolOrchestrator


def test_sbt_ai_context_is_registered():
    orchestrator = ToolOrchestrator()
    assert "sbt_ai_context" in {item["name"] for item in orchestrator.available()}


@pytest.mark.asyncio
async def test_sbt_ai_context_returns_no_evidence_when_mt4_is_disconnected():
    orchestrator = ToolOrchestrator()
    payload = {
        "contract": "bitey-sbt-ai-context-v1",
        "mt4": {"connected": False, "last_seen": None},
        "bot": {"connected": False},
        "analysis": {"state": "WAITING_FOR_MT4"},
        "optimization": {"state": "WAITING_FOR_MT4"},
        "activity": [],
    }
    request = httpx.Request("GET", "https://bitey-system-bots-trading-api.onrender.com/api/v1/ai-bot-lab/context")
    response = httpx.Response(200, json=payload, request=request)
    with patch("app.core.tool_orchestrator.httpx.AsyncClient") as client_cls:
        client = client_cls.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.get = AsyncMock(return_value=response)
        result = await orchestrator._sbt_ai_context("qué bot está activo", {})
    assert result["ok"] is True
    assert result["observed"] is False
    assert result["verified"] is False
    assert "No active bot" in result["evidence"]


def test_bot_question_selects_general_sbt_context():
    orchestrator = ToolOrchestrator()
    decision = orchestrator.cognitive_selection("¿qué bot está activo?", {})
    assert decision["selected_tools"] == ["sbt_ai_context"]
