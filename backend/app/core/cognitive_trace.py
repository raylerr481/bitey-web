from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4


@dataclass
class CognitiveTrace:
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    conversation_id: str | None = None
    request_id: str | None = None
    message_hash: str = ""
    decision: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    provider: dict[str, Any] = field(default_factory=dict)
    evaluation: dict[str, Any] = field(default_factory=dict)
    revision: dict[str, Any] = field(default_factory=dict)
    final_status: str = "running"

    @staticmethod
    def hash_message(message: str) -> str:
        return sha256(message.encode("utf-8")).hexdigest()

    def snapshot(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "created_at": self.created_at,
            "conversation_id": self.conversation_id,
            "request_id": self.request_id,
            "message_hash": self.message_hash,
            "decision": self.decision,
            "tools": self.tools,
            "evidence": self.evidence,
            "provider": self.provider,
            "evaluation": self.evaluation,
            "revision": self.revision,
            "final_status": self.final_status,
        }


class CognitiveTraceStore:
    """Bounded local observability store; no raw prompts/responses are persisted."""

    def __init__(self, max_items: int = 500) -> None:
        self.max_items = max(50, max_items)
        self._items: dict[str, CognitiveTrace] = {}

    def start(self, message: str, conversation_id: str, request_id: str | None = None) -> CognitiveTrace:
        trace = CognitiveTrace(
            conversation_id=conversation_id,
            request_id=request_id,
            message_hash=CognitiveTrace.hash_message(message),
        )
        self._items[trace.trace_id] = trace
        self._trim()
        return trace

    def get(self, trace_id: str) -> CognitiveTrace | None:
        return self._items.get(trace_id)

    def finish(self, trace: CognitiveTrace, status: str) -> None:
        trace.final_status = status
        self._items[trace.trace_id] = trace
        self._trim()

    def recent(self, conversation_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        items = list(self._items.values())
        if conversation_id:
            items = [item for item in items if item.conversation_id == conversation_id]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return [item.snapshot() for item in items[: max(1, min(limit, 100))]]

    def _trim(self) -> None:
        while len(self._items) > self.max_items:
            oldest = min(self._items.values(), key=lambda item: item.created_at)
            self._items.pop(oldest.trace_id, None)
