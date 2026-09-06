from app.core.context_engine import ContextEngine


def test_enterprise_context_is_optional_and_does_not_break_general_context():
    context = ContextEngine().assemble(message="hello", metadata={"user": {"id": "u1"}})
    payload = context.as_dict()
    assert payload["enterprise"] is None
    assert payload["task"]["message"] == "hello"


def test_request_enterprise_context_is_normalized():
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
    )
    enterprise = context.as_dict()["enterprise"]
    assert enterprise["company_id"] == "demo-1"
    assert enterprise["company_name"] == "Demo Company"
    assert enterprise["website"] == "https://example.com"
    assert enterprise["services"] == ["support"]
    assert enterprise["directives"]["tone"] == "professional"
