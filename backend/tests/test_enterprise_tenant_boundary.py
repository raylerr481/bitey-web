from app.core.capability_boundary import classify_server_capability
from app.core.context_engine import ContextEngine
from app.core.execution_context import build_execution_context
from app.core.tenant_resolver import resolve_tenant_id


def test_server_capability_uses_current_message_only():
    assert classify_server_capability("Necesito una campaña de marketing digital") == "enterprise"
    assert classify_server_capability("¿Qué es Bitcoin?") == "general"


def test_client_tenant_metadata_is_not_authoritative(monkeypatch):
    monkeypatch.delenv("BITEY_USER_TENANT_MAP_JSON", raising=False)
    assert resolve_tenant_id("user-a") is None


def test_enterprise_context_requires_trusted_tenant(monkeypatch):
    monkeypatch.setenv("BITEY_ENTERPRISE_TENANT_ID", "tenant-a")
    monkeypatch.setenv("BITEY_ENTERPRISE_COMPANY_ID", "company-a")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    engine = ContextEngine()
    public_context = engine.assemble(
        message="Diseña una campaña de marketing digital",
        metadata={"enterprise": {"company_name": "attacker-controlled"}, "tenant_id": "tenant-a"},
        execution_context=build_execution_context(
            conversation_id="conv-a",
            trusted_tenant_id="public",
            trusted_user_id="user-a",
            trusted_channel="web",
            trusted_module_id="enterprise",
        ),
    )
    assert public_context.enterprise is None


def test_enterprise_context_can_only_follow_server_trusted_tenant(monkeypatch):
    monkeypatch.setenv("BITEY_ENTERPRISE_TENANT_ID", "tenant-a")
    monkeypatch.setenv("BITEY_ENTERPRISE_COMPANY_ID", "company-a")

    engine = ContextEngine()
    engine.enterprise_resolver._load_company = lambda company_id: {
        "company_id": company_id,
        "company_name": "Tenant A",
        "source": "supabase",
        "authoritative": True,
    }

    context = engine.assemble(
        message="Necesito mejorar mi SEO",
        metadata={"enterprise": {"company_name": "attacker-controlled"}},
        execution_context=build_execution_context(
            conversation_id="conv-a",
            trusted_tenant_id="tenant-a",
            trusted_user_id="user-a",
            trusted_channel="web",
            trusted_module_id="enterprise",
        ),
    )

    assert context.enterprise is not None
    assert context.enterprise["company_id"] == "company-a"
    assert context.enterprise["tenant_id"] == "tenant-a"
    assert context.enterprise["company_name"] == "Tenant A"
