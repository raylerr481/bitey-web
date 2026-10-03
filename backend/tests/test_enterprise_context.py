from app.core.context_engine import ContextEngine


def test_enterprise_context_is_optional_and_does_not_break_general_context():
    context = ContextEngine().assemble(message="hello", metadata={"user": {"id": "u1"}})
    payload = context.as_dict()
    assert payload["enterprise"] is None
    assert payload["task"]["message"] == "hello"


def test_untrusted_enterprise_metadata_is_not_activated():
    context = ContextEngine().assemble(
        message="what services do you offer?",
        metadata={"enterprise": {"company_id": "demo-1", "company_name": "Demo Company"}},
    )
    assert context.as_dict()["enterprise"] is None
