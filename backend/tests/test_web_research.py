from app.core.multi_step_research import MultiStepResearchRuntime, ResearchEvidencePackage
from app.core.research_engine import ResearchEngine


def test_dynamic_question_requires_web_research():
    plan = ResearchEngine().plan("¿Qué temperatura hay actualmente en Esteio?")
    assert plan.required is True
    assert plan.strategy in {"web_lookup", "multi_source_research"}


def test_explicit_research_uses_multi_source_strategy():
    plan = ResearchEngine().plan("Investiga esta plataforma y contrasta fuentes")
    assert plan.required is True
    assert plan.strategy == "multi_source_research"
    assert plan.confidence > 0


def test_static_question_does_not_force_web():
    plan = ResearchEngine().plan("¿Qué es una dirección IP?")
    assert plan.required is False
    assert plan.strategy == "none"


def test_url_requires_web():
    plan = ResearchEngine().plan("Revisa https://example.com y dime qué es")
    assert plan.required is True


def test_runtime_decomposes_and_deduplicates():
    runtime = MultiStepResearchRuntime()
    subs = runtime.decompose("Investiga una plataforma de trading", explicit_research=True)
    assert 3 <= len(subs) <= 5
    assert len(runtime.build_queries(subs)) >= 1

    package = ResearchEvidencePackage("Investiga una plataforma de trading")
    runtime.merge_evidence(package, [
        {"url": "https://a.example", "ok": True, "content": "source a"},
        {"url": "https://b.example", "ok": True, "content": "source b"},
        {"url": "https://a.example", "ok": True, "content": "duplicate"},
    ], 1)
    assert len(package.evidence) == 2
    assert package.sufficient is True


def test_runtime_allows_second_pass_when_evidence_is_weak():
    runtime = MultiStepResearchRuntime(max_passes=3)
    package = ResearchEvidencePackage("pregunta")
    runtime.merge_evidence(package, [{"url": "https://a.example", "ok": True, "content": "one source"}], 1)
    assert package.sufficient is False
    assert runtime.next_pass_needed(package) is True
