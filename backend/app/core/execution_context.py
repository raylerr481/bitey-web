from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

_ALLOWED_MODULES = {"general", "bitefixes", "jobia", "sbt"}
_ALLOWED_CHANNELS = {"web", "api", "telegram", "whatsapp", "messenger", "app", "unknown"}

@dataclass(frozen=True)
class ExecutionContext:
    """Canonical execution scope used to keep tenant, identity and memory boundaries explicit."""
    tenant_id: str
    user_id: str
    actor_type: str
    channel: str
    conversation_id: str
    module_id: str

    @property
    def memory_scope(self) -> str:
        return f"tenant:{self.tenant_id}:user:{self.user_id}:module:{self.module_id}:conversation:{self.conversation_id}"

    def as_dict(self) -> dict[str, Any]:
        return {"identity":{"user_id":self.user_id,"actor_type":self.actor_type},"tenant":{"tenant_id":self.tenant_id},"session":{"conversation_id":self.conversation_id,"channel":self.channel},"module":{"module_id":self.module_id},"memory":{"memory_scope":self.memory_scope}}

def build_execution_context(*, conversation_id: str, metadata: dict[str, Any] | None = None, trusted_tenant_id: str | None = None, trusted_user_id: str | None = None, trusted_channel: str | None = None, trusted_module_id: str | None = None) -> ExecutionContext:
    """Build scope from trusted server values; client metadata is never authoritative."""
    del metadata
    tenant_id = str(trusted_tenant_id or "public").strip() or "public"
    user_id = str(trusted_user_id or "anonymous").strip() or "anonymous"
    channel = str(trusted_channel or "unknown").strip().lower()
    module_id = str(trusted_module_id or "general").strip().lower()
    if channel not in _ALLOWED_CHANNELS: channel = "unknown"
    if module_id not in _ALLOWED_MODULES: module_id = "general"
    return ExecutionContext(tenant_id=tenant_id,user_id=user_id,actor_type="anonymous" if user_id == "anonymous" else "user",channel=channel,conversation_id=str(conversation_id),module_id=module_id)

def server_execution_context(conversation_id: str) -> ExecutionContext:
    """Resolve deployment scope from server configuration, never request metadata."""
    return build_execution_context(conversation_id=conversation_id,trusted_tenant_id=os.getenv("BITEY_TENANT_ID","public"),trusted_user_id=os.getenv("BITEY_DEFAULT_USER_ID","anonymous"),trusted_channel=os.getenv("BITEY_DEFAULT_CHANNEL","api"),trusted_module_id=os.getenv("BITEY_DEFAULT_MODULE","general"))
