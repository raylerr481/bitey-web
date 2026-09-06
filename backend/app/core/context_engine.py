from dataclasses import dataclass, field
from typing import Any
import os

from .enterprise_context import EnterpriseContextResolver


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
    """Build dynamic general context with optional tenant/company enrichment."""

    def __init__(self) -> None:
        self.enterprise_resolver = EnterpriseContextResolver()

    def assemble(self, *, message: str, metadata: dict[str, Any] | None = None) -> ContextEnvelope:
        metadata = metadata or {}
        has_enterprise_hint = bool(
            metadata.get("enterprise")
            or metadata.get("company_id")
            or metadata.get("enterprise_company_id")
            or os.getenv("BITEY_ENTERPRISE_PROFILE_JSON")
        )
        enterprise = self.enterprise_resolver.resolve(metadata) if has_enterprise_hint else None
        return ContextEnvelope(
            user=metadata.get("user", {}),
            conversation=metadata.get("conversation", {}),
            task={"message": message, **metadata.get("task", {})},
            research=metadata.get("research", {}),
            enterprise=enterprise,
            channel=metadata.get("channel", {}),
        )
