from types import SimpleNamespace

from app.core.cognitive_architecture import BiteyCognitiveArchitecture
from app.core.provider_gateway import ProviderGateway, ProviderHealth


def test_malformed_nasa_question_reaches_conceptual_path():
    architecture = BiteyCognitiveArchitecture()
    result = architecture.run("que e sla nasa", {})
    frame = result["frame"]
    assert frame["domain"] == "general"
    assert frame["evidence_required"] is True
    assert architecture._normalize_for_routing("que e sla nasa") == "qué es la nasa"


def test_provider_tiers_keep_ollama_before_cloud():
    gateway = ProviderGateway.__new__(ProviderGateway)
    gateway._provider_health = {
        "ollama-local": ProviderHealth(successes=1, failures=5, ewma_latency_ms=1500),
        "cloudflare-workers-ai-free": ProviderHealth(successes=10, failures=0, ewma_latency_ms=80),
        "groq-free": ProviderHealth(successes=10, failures=0, ewma_latency_ms=60),
    }
    providers = [
        SimpleNamespace(name="groq-free", priority=50, free_only=True),
        SimpleNamespace(name="cloudflare-workers-ai-free", priority=40, free_only=True),
        SimpleNamespace(name="ollama-local", priority=1000, free_only=True),
    ]
    ordered = gateway._order_for_role(providers, "synthesis")
    assert [item.name for item in ordered] == [
        "ollama-local",
        "cloudflare-workers-ai-free",
        "groq-free",
    ]
