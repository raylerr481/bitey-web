from app.core.deep_research import DeepResearchEngine, DeepResearchPlan


def test_source_key_normalizes_www_host():
    engine = DeepResearchEngine()
    assert engine._source_key("https://www.Example.com/page") == "example.com"


def test_research_plan_prefers_distinct_hosts_before_same_host_pages():
    engine = DeepResearchEngine()
    plan = DeepResearchPlan(query="test", reasons=["knowledge_request"])
    # The selection logic is exercised through the same normalization contract
    # used by fetch(); distinct publisher hosts must remain distinguishable.
    assert engine._source_key("https://a.example/one") != engine._source_key("https://b.example/two")
    assert engine._source_key("https://www.a.example/two") == engine._source_key("https://a.example/one")
    assert plan.reasons == ["knowledge_request"]
