import asyncio

from app.core.multistep_runtime import MultiStepResearchRuntime


class FakeResearch:
    def plan(self, query, context=None):
        return {"query": query}

    async def fetch(self, plan):
        return plan

    def source_summary(self, plan):
        return [{"url": "https://example.test", "title": plan["query"], "ok": True}]

    def evidence_context(self, plan):
        return f"Evidence for {plan['query']}"


def test_runtime_is_bounded_and_decomposes_evidence_first_queries():
    runtime = MultiStepResearchRuntime(max_steps=99, max_sources_per_step=99)
    assert runtime.max_steps == 8
    assert runtime.max_sources_per_step == 8
    assert runtime.status()["unbounded_execution"] is False

    queries = runtime._queries(
        "investiga y compara esta arquitectura",
        {"reasoning_mode": "evidence_first"},
    )
    assert len(queries) <= 8
    assert queries[0] == "investiga y compara esta arquitectura"
    assert len(queries) == len(set(queries))


def test_runtime_returns_structured_bounded_result():
    runtime = MultiStepResearchRuntime(max_steps=2, max_sources_per_step=1)
    runtime.research = FakeResearch()

    result = asyncio.run(runtime.run("investiga Bitey IA"))

    assert result.bounded is True
    assert result.original_query == "investiga Bitey IA"
    assert 1 <= len(result.steps) <= 2
    assert all(step.status == "completed" for step in result.steps)
    assert result.evidence_context
    assert result.decision["evidence_required"] is True
