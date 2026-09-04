from app.core.capability_registry import CapabilityRegistry


def test_registry_exposes_core_workspace_capabilities():
    registry = CapabilityRegistry()
    ids = {item["id"] for item in registry.available()}

    assert {"general", "research", "documents", "slides", "sheets", "images", "websites", "developer", "video", "audio", "skills", "automations", "markets"}.issubset(ids)


def test_registry_resolves_market_domain_without_enabling_execution():
    registry = CapabilityRegistry()
    selected = registry.resolve(domain="trading")

    assert [item.id for item in selected] == ["markets"]
    assert selected[0].risk == "high"
    assert selected[0].metadata["execution_boundary"] == "sbt_risk_gate"
    assert selected[0].metadata["live_trading"] is False


def test_registry_resolves_workspace_mode_directly():
    registry = CapabilityRegistry()

    assert registry.resolve(mode="slides")[0].id == "slides"
    assert registry.resolve(mode="developer")[0].id == "developer"
