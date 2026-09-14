from app.core.context_engine import ContextEngine
from app.core.execution_context import build_execution_context


def test_enterprise_context_is_optional_and_does_not_break_general_context():
    context = ContextEngine().assemble(message="hello", metadata={"user": {"id": "u1"}})
    payload = context.as_dict()
    assert payload["enterprise"] is None
    assert payload["task"]["message"] == "hello"


def test_request_enterprise_context_is_normalized():
    execution = build_execution_context(
        conversation_id="demo-conversation",
        trusted_tenant_id="demo-tenant",
        trusted_user_id="demo-user",
        trusted_channel="web",
        trusted_module_id="enterprise",
    )
    context = ContextEngine().assemble(
        message="what services do you offer?",
        metadata={
            "enterprise": {
                "company_id": "demo-1",
                "company_name": "Demo Company",
                "website": "https://example.com",
                "services": ["support"],
                "directives": {"tone": "professional"},
            }
        },
        execution_context=execution,
    )
    enterprise = context.as_dict()["enterprise"]
    assert context.as_dict()["capability"] == "enterprise"
    assert enterprise["company_id"] == "demo-1"
    assert enterprise["company_name"] == "Demo Company"
    assert enterprise["website"] == "https://example.com"
    assert enterprise["services"] == ["support"]
    assert enterprise["directives"]["tone"] == "professional"
    assert enterprise["authoritative"] is False
    assert enterprise["source"] == "client_metadata"
    assert enterprise["capability"] == "enterprise"


def test_general_execution_does_not_accept_client_enterprise_context():
    execution = build_execution_context(
        conversation_id="demo-conversation",
        trusted_tenant_id="demo-tenant",
        trusted_user_id="demo-user",
        trusted_channel="web",
        trusted_module_id="general",
    )
    context = ContextEngine().assemble(
        message="what is CRM?",
        metadata={"enterprise": {"company_id": "demo-1", "company_name": "Demo Company"}},
        execution_context=execution,
    )
    assert context.as_dict()["capability"] == "general"
    assert context.as_dict()["enterprise"] is None
