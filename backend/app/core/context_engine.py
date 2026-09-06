from dataclasses import dataclass, field
from typing import Any
import os

from .enterprise_context import EnterpriseContextResolver
from .bitefixes_context_bridge import BiteFixesContextBridge


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
    """Build general context first; enterprise context is opt-in and read-only."""

    def __init__(self) -> None:
        self.enterprise_resolver = EnterpriseContextResolver()
        self.bitefixes_bridge = BiteFixesContextBridge()

    def assemble(self, *, message: str, metadata: dict[str, Any] | None = None) -> ContextEnvelope:
        metadata = metadata or {}
        has_enterprise_hint = bool(
            metadata.get("enterprise")
            or metadata.get("company_id")
            or metadata.get("enterprise_company_id")
            or os.getenv("BITEY_ENTERPRISE_PROFILE_JSON")
        )
        enterprise = self.enterprise_resolver.resolve(metadata) if has_enterprise_hint else None
        company_id = metadata.get("company_id") or metadata.get("enterprise_company_id")
        if company_id and self.bitefixes_bridge.configured:
            remote = self.bitefixes_bridge.company_sync(str(company_id))
            if remote:
                enterprise = {
                    "company_id": str(company_id),
                    "company": remote.get("company") or {},
                    "profile": remote.get("profile") or {},
                    "source": "bitefixes_backend",
                    "read_only": True,
                    "authoritative": True,
                }
        return ContextEnvelope(
            user=metadata.get("user", {}),
            conversation=metadata.get("conversation", {}),
            task={"message": message, **metadata.get("task", {})},
            research=metadata.get("research", {}),
            enterprise=enterprise,
            channel=metadata.get("channel", {}),
        )

    async def enrich_from_bitefixes(self, context: ContextEnvelope, metadata: dict[str, Any] | None = None) -> ContextEnvelope:
        """Fetch enterprise context only when a company is explicitly identified."""
        metadata = metadata or {}
        company_id = metadata.get("company_id") or metadata.get("enterprise_company_id")
        if not company_id or not self.bitefixes_bridge.configured:
            return context
        remote = await self.bitefixes_bridge.company(str(company_id))
        if remote:
            context.enterprise = {
                "company_id": str(company_id),
                "company": remote.get("company") or {},
                "profile": remote.get("profile") or {},
                "source": "bitefixes_backend",
                "read_only": True,
                "authoritative": True,
            }
        return context
