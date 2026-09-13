from app.core.module_registry import ModuleRegistry, ModuleSpec


def test_general_domain_never_resolves_specialized_modules():
    registry = ModuleRegistry()
    registry.register(
        ModuleSpec(
            "sbt",
            "Trading module",
            capabilities=("trading", "market_intelligence"),
            enabled=True,
        )
    )

    assert registry.resolve_for_domain("general") == []
    assert registry.resolve_for_domain("") == []
    assert [module.name for module in registry.resolve_for_domain("trading")] == ["sbt"]
