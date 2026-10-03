from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.chat_v2 import ChatV2Request, ChatV2Response, create_chat_v2_router


class _ExplodingCognition:
    def _is_greeting(self, _value: str) -> bool:
        raise RuntimeError("SECRET_INTERNAL_PROVIDER_FAILURE")


class _StableCognition:
    def _is_greeting(self, value: str) -> bool:
        return value in {"hola", "hello"}


class _Tools:
    def available(self):
        return []


class _Memory:
    async def create_conversation(self, _cid, _metadata):
        return None


def _endpoint(cognition):
    router = create_chat_v2_router(
        memory=_Memory(),
        providers=SimpleNamespace(),
        tools=_Tools(),
        brain=SimpleNamespace(),
        cognition=cognition,
    )
    route = next(item for item in router.routes if getattr(item, "path", "") == "/api/v2/chat")
    return route.endpoint


def test_chat_v2_internal_failure_returns_safe_response():
    async def run():
        endpoint = _endpoint(_ExplodingCognition())
        payload = ChatV2Request(
            conversation_id="00000000-0000-0000-0000-000000000001",
            message="qué es la NASA",
        )
        return await endpoint(payload)

    response = asyncio.run(run())

    assert isinstance(response, ChatV2Response)
    assert response.answer_validation["decision"] == "accept"
    assert response.answer_validation["provenance"] == "bitey_native_recovery"
    assert response.execution_state["recoverable"] is True
    assert "SECRET_INTERNAL_PROVIDER_FAILURE" not in response.answer
    assert response.tools_used == ["bitey-native-recovery"]
    assert response.sources == []


def test_chat_v2_greeting_stays_available_without_external_provider():
    async def run():
        endpoint = _endpoint(_StableCognition())
        payload = ChatV2Request(
            conversation_id="00000000-0000-0000-0000-000000000001",
            message="hola",
        )
        return await endpoint(payload)

    response = asyncio.run(run())

    assert response.answer.startswith("¡Hola!")
    assert response.mode == "chat"
    assert response.tools_used == []
    assert response.answer_validation["valid"] is True


def test_chat_v2_request_rejects_empty_message():
    with pytest.raises(Exception):
        ChatV2Request(message="")


def test_chat_v2_response_requires_uuid_like_conversation_id_contract():
    response = ChatV2Response(
        conversation_id="00000000-0000-0000-0000-000000000001",
        answer="ok",
        mode="chat",
        elapsed_ms=1,
    )
    UUID(response.conversation_id)
