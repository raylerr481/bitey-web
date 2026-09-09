from dataclasses import dataclass, field
from typing import Any
import os

from .enterprise_context import EnterpriseContextResolver
from .bitefixes_context_bridge import BiteFixesContextBridge
from .execution_context import ExecutionContext, server_execution_context


@dataclass
class ContextEnvelope:
    """Dynamic context assembled for one execution; enterprise context is optional."""

    user: dict[str, Any] = field(default_factory=dict)
    conversation: dict[str, Any] = field(default_factory=dict)
    task: dict[str, Any] = field(default_factory=dict)
    research: dict[str, Any] = field(default_factory=dict)
    enterprise: dict[str, Any] | None = None
    channel: dict[str, Any] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "conversation": self.conversation,
            "task": self.task,
            "research": self.research,
            "enterprise": self.enterprise,
            "channel": self.channel,
            "execution": self.execution,
        }


class ContextEngine:
    """Build general context first; enterprise context is opt-in and server-scoped."""

    def __init__(self) -> None:
        self.enterprise_resolver = EnterpriseContextResolver()
        self.bitefixes_bridge = BiteFixesContextBridge()

    def assemble(
        self,
        *,
        message: str,
        metadata: dict[str, Any] | None = None,
        execution_context: ExecutionContext | None = None,
        conversation_id: str | None = None,
    ) -> ContextEnvelope:
        metadata = metadata or {}
        enterprise = None

        # Every normal execution receives a server-derived scope. Client metadata
        # can enrich context, but cannot select tenant, identity, module or company.
        if execution_context is None and conversation_id:
            execution_context = server_execution_context(conversation_id)

        # BiteFixes context is available only when the server has established the
        # BiteFixes tenant and the company identifier is configured server-side.
        if execution_context is not None and execution_context.tenant_id == "bitefixes":
            company_id = os.getenv("BITEFIXES_COMPANY_ID", "").strip()
            if company_id and self.bitefixes_bridge.configured:
                remote = self.bitefixes_bridge.company_sync(company_id)
                if remote:
                    enterprise = {
                        "company_id": company_id,
                        "company": remote.get("company") or {},
                        "profile": remote.get("profile") or {},
                        "source": "bitefixes_backend",
                        "read_only": True,
                        "authoritative": True,
                    }
        elif execution_context is None and os.getenv("BITEY_ENTERPRISE_PROFILE_JSON"):
            # Preserve the existing static enterprise profile behavior only for
            # callers that do not provide a conversation scope.
            enterprise = self.enterprise_resolver.resolve({})

        return ContextEnvelope(
            user=metadata.get("user", {}) if isinstance(metadata.get("user", {}), dict) else {},
            conversation=metadata.get("conversation", {}) if isinstance(metadata.get("conversation", {}), dict) else {},
            task={"message": message, **(metadata.get("task", {}) if isinstance(metadata.get("task", {}), dict) else {})},
            research=metadata.get("research", {}) if isinstance(metadata.get("research", {}), dict) else {},
            enterprise=enterprise,
            channel=metadata.get("channel", {}) if isinstance(metadata.get("channel", {}), dict) else {},
            execution=execution_context.as_dict() if execution_context is not None else {},
        )

    async def enrich_from_bitefixes(
        self,
        context: ContextEnvelope,
        metadata: dict[str, Any] | None = None,
        execution_context: ExecutionContext | None = None,
    ) -> ContextEnvelope:
        """Fetch BiteFixes context only for a server-established BiteFixes tenant."""
        if execution_context is None:
            conversation_id = str(context.execution.get("session", {}).get("conversation_id") or "").strip()
            if conversation_id:
                execution_context = server_execution_context(conversation_id)
        if execution_context is None or execution_context.tenant_id != "bitefixes":
            return context
        company_id = os.getenv("BITEFIXES_COMPANY_ID", "").strip()
        if not company_id or not self.bitefixes_bridge.configured:
            return context
        remote = await self.bitefixes_bridge.company(company_id)
        if remote:
            context.enterprise = {
                "company_id": company_id,
                "company": remote.get("company") or {},
                "profile": remote.get("profile") or {},
                "source": "bitefixes_backend",
                "read_only": True,
                "authoritative": True,
            }
        context.execution = execution_context.as_dict()
        return context
