from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextEnvelope:
    """Dynamic context assembled for one execution; enterprise context is optional."""

    user: dict[str, Any] = field(default_factory=dict)
    conversation: dict[str, Any] = field(default_factory=dict)
    task: dict[str, Any] = field(default_factory=dict)
    research: dict[str, Any] = field(default_factory=dict)
    enterprise: dict[str, Any] | None = None
    channel: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "conversation": self.conversation,
            "task": self.task,
            "research": self.research,
            "enterprise": self.enterprise,
            "channel": self.channel,
        }


class ContextEngine:
    """Builds context without imposing a fixed business domain."""

    def assemble(self, *, message: str, metadata: dict[str, Any] | None = None) -> ContextEnvelope:
        metadata = metadata or {}
        return ContextEnvelope(
            user=metadata.get("user", {}),
            conversation=metadata.get("conversation", {}),
            task={"message": message, **metadata.get("task", {})},
            research=metadata.get("research", {}),
            enterprise=metadata.get("enterprise"),
            channel=metadata.get("channel", {}),
        )
