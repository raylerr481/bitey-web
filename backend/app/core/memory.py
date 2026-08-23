from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryStore:
    """Minimal in-process memory boundary; persistent storage is an adapter later."""

    conversations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def append(self, conversation_id: str, message: dict[str, Any]) -> None:
        self.conversations.setdefault(conversation_id, []).append(message)

    def history(self, conversation_id: str) -> list[dict[str, Any]]:
        return list(self.conversations.get(conversation_id, []))
