from types import SimpleNamespace

from app.core.cognitive_architecture import BiteyCognitiveArchitecture
from app.core.provider_gateway import ProviderGateway, ProviderHealth


def test_malformed_nasa_question_reaches_conceptual_path():
    architecture = BiteyCognitiveArchitecture()
    result = architecture.run("que e sla nasa", {})
    frame = result["frame"]
    assert frame["domain"] == "general"
    assert frame["evidence_required"] is False
    assert architecture._normalize_for_routing("que e sla nasa") == "qué es la nasa"


def test_omitted_verb_concept_question_reaches_knowledge_path():
    from app.core.cognitive_model import CognitiveModel

    model = CognitiveModel()
    normalized = model._normalize_for_routing("que el adn")
    state = model.process("que el adn", {})

    assert normalized == "qué es el adn"
    assert state.intention["intent_family"] == "knowledge"
    assert state.intention["domain"] == "general"
    assert state.plan["needs_evidence"] is False


def test_shorthand_concept_normalization_handles_articles_without_literal_escape_artifacts():
    from app.core.cognitive_model import CognitiveModel

    model = CognitiveModel()
    for raw, expected in (
        ("que el adn", "qué es el adn"),
        ("que la nasa", "qué es la nasa"),
        ("qué los satélites", "qué es los satélites"),
    ):
        assert model._normalize_for_routing(raw) == expected


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


def test_simple_concept_does_not_require_web_evidence():
    from app.core.cognitive_model import CognitiveModel
    model = CognitiveModel()
    state = model.process("qué es la NASA", {})
    assert state.plan["needs_evidence"] is False
    assert state.plan["tool_strategy"] == ["llm_synthesis"]


def test_native_stable_concepts_are_available_without_web():
    import asyncio
    from app.core.native_model import NativeReasoningModel

    async def run():
        context = {}
        answer = await NativeReasoningModel().generate(
            messages=[{"role": "user", "content": "que e sla nasa"}],
            context=context,
        )
        return answer, context

    answer, context = asyncio.run(run())
    assert "NASA" in answer
    assert context["native_grounded_type"] == "stable_concept"


def test_native_rocket_definition_is_available_without_web():
    import asyncio
    from app.core.native_model import NativeReasoningModel

    async def run():
        context = {}
        answer = await NativeReasoningModel().generate(
            messages=[{"role": "user", "content": "que es un cohete"}],
            context=context,
        )
        return answer, context

    answer, context = asyncio.run(run())
    assert "cohete" in answer.lower() or "cohete espacial" in answer.lower()
    assert context["native_grounded_type"] == "stable_concept"


def test_current_bitcoin_price_uses_generic_web_evidence_not_sbt():
    from app.core.bitey_brain import BiteyBrain

    ctx = {}
    state = BiteyBrain().think("¿Cuál es el precio de Bitcoin ahora?", ctx)
    assert "web_research" in state.tool_priority
    assert "sbt_market" not in state.tool_priority


def test_portuguese_tempo_routes_to_weather():
    from app.core.cognitive_model import CognitiveModel
    model = CognitiveModel()

    state = model.process("tempo em Esteio", {})
    assert state.intention["intent_family"] == "weather"
    assert "weather" in state.plan["tool_strategy"]


def test_common_tempo_typo_is_normalized_for_routing():
    from app.core.cognitive_model import CognitiveModel
    model = CognitiveModel()

    state = model.process("timepoe em Esteio", {})
    assert state.intention["intent_family"] == "weather"


def test_brain_tool_policy_has_no_undefined_intent_family_dependency():
    from app.core.bitey_brain import BiteyBrain

    brain = BiteyBrain()
    state = brain.think(
        "¿Cuál es el precio de Bitcoin ahora?",
        {
            "cognition": {
                "perception": {"question": True},
                "intention": {
                    "domain": "trading",
                    "intent_family": "current_info",
                },
                "plan": {
                    "needs_evidence": True,
                    "freshness_required": True,
                    "tool_strategy": ["web_research"],
                },
            }
        },
    )
    assert "web_research" in state.tool_priority
    assert "sbt_market" not in state.tool_priority


def test_stable_conceptual_question_remains_general_knowledge():
    from app.core.bitey_brain import BiteyBrain

    state = BiteyBrain().think("¿Qué es un cohete?", {})
    assert state.task_class == "general"
    assert not state.evidence_required
    assert "web_research" not in state.tool_priority


def test_degraded_provider_answer_is_detected_for_native_recovery():
    from app.chat_v2 import _is_degraded_answer

    assert _is_degraded_answer("Ahora mismo no puedo completar esta consulta de forma segura.")
    assert _is_degraded_answer("I can't complete this request right now.")
    assert not _is_degraded_answer("Un cohete genera empuje expulsando gases a gran velocidad.")
