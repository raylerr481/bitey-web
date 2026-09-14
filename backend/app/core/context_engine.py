from dataclasses import dataclass, field
from typing import Any
import os

from .enterprise_context import EnterpriseContextResolver
from .bitefixes_context_bridge import BiteFixesContextBridge
from .execution_context import ExecutionContext, server_execution_context


@dataclass
class ContextEnvelope:
    """Dynamic context assembled for one execution; specialized context is capability-scoped."""

    user: dict[str, Any] = field(default_factory=dict)
    conversation: dict[str, Any] = field(default_factory=dict)
    task: dict[str, Any] = field(default_factory=dict)
    research: dict[str, Any] = field(default_factory=dict)
    enterprise: dict[str, Any] | None = None
    channel: dict[str, Any] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)
    capability: str = "general"

    def as_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "conversation": self.conversation,
            "task": self.task,
            "research": self.research,
            "enterprise": self.enterprise,
            "channel": self.channel,
            "execution": self.execution,
            "capability": self.capability,
        }


class ContextEngine:
    """Build general context first; specialized context is explicitly capability-scoped."""

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

        if execution_context is None and conversation_id:
            execution_context = server_execution_context(conversation_id)

        capability = execution_context.capability if execution_context is not None else "general"

        # BiteFixes is a tenant/integration scope for General, not Enterprise.
        # Company context must never turn a normal BiteFixes conversation into
        # an Enterprise execution implicitly.
        if execution_context is not None and execution_context.tenant_id == "bitefixes":
            if capability == "enterprise":
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
                            "capability": "enterprise",
                        }
        elif execution_context is not None and capability == "enterprise":
            # Enterprise context is private. Client metadata is never an
            # authority and a global profile is never sufficient for access.
            tenant_id = execution_context.tenant_id.strip()
            configured_tenant = os.getenv("BITEY_ENTERPRISE_TENANT_ID", "").strip()
            company_id = os.getenv("BITEY_ENTERPRISE_COMPANY_ID", "").strip()
            if tenant_id and tenant_id != "public" and configured_tenant and tenant_id == configured_tenant and company_id:
                enterprise = self.enterprise_resolver._load_company(company_id)
                if enterprise:
                    enterprise["tenant_id"] = tenant_id
                    enterprise["capability"] = "enterprise"
                    enterprise["read_only"] = True
                    enterprise["authoritative"] = True

        return ContextEnvelope(
            user=metadata.get("user", {}) if isinstance(metadata.get("user", {}), dict) else {},
            conversation=metadata.get("conversation", {}) if isinstance(metadata.get("conversation", {}), dict) else {},
            task={"message": message, **(metadata.get("task", {}) if isinstance(metadata.get("task", {}), dict) else {})},
            research=metadata.get("research", {}) if isinstance(metadata.get("research", {}), dict) else {},
            enterprise=enterprise,
            channel=metadata.get("channel", {}) if isinstance(metadata.get("channel", {}), dict) else {},
            execution=execution_context.as_dict() if execution_context is not None else {},
            capability=capability,
        )

    async def enrich_from_bitefixes(
        self,
        context: ContextEnvelope,
        metadata: dict[str, Any] | None = None,
        execution_context: ExecutionContext | None = None,
    ) -> ContextEnvelope:
        """Fetch company context only for an explicitly Enterprise execution."""
        if execution_context is None:
            conversation_id = str(context.execution.get("session", {}).get("conversation_id") or "").strip()
            if conversation_id:
                execution_context = server_execution_context(conversation_id)
        if execution_context is None or execution_context.tenant_id != "bitefixes":
            return context
        if execution_context.capability != "enterprise":
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
                "capability": "enterprise",
            }
        context.execution = execution_context.as_dict()
        context.capability = execution_context.capability
        return context
