import pytest

from app.core.multi_step_research import MultiStepResearchRuntime


@pytest.mark.asyncio
async def test_runtime_deduplicates_and_stops_when_sufficient():
    calls = []

    async def researcher(query, context):
        calls.append((query, context["research_pass"]))
        return {"evidence": [{"url": "https://example.test/a", "content": "evidence"}], "sufficient": True}

    runtime = MultiStepResearchRuntime(researcher, max_subquestions=3, max_passes=2, max_sources=8)
    result = await runtime.run("Q", subquestions=["Q", "q"])

    assert result.stopped_early is True
    assert result.stop_reason == "evidence_sufficient"
    assert len(result.queries) == 1
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_runtime_never_exceeds_source_bound():
    async def researcher(query, context):
        return {"evidence": [{"url": f"https://example.test/{i}"} for i in range(10)], "sufficient": False}

    runtime = MultiStepResearchRuntime(researcher, max_subquestions=2, max_passes=2, max_sources=3)
    result = await runtime.run("Q", subquestions=["Q2"])

    assert len(result.evidence) == 3
    assert result.stop_reason == "max_sources"
    assert result.passes <= 2
