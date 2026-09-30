import asyncio

from app.core.tool_orchestrator import ToolOrchestrator, ToolSpec


def test_multi_tool_execution_normalizes_provenance():
    orchestrator = ToolOrchestrator()

    async def first(**kwargs):
        return {"ok": True, "evidence": "first"}

    async def second(**kwargs):
        return {"ok": True, "evidence": "second"}

    orchestrator.register(
        ToolSpec("test_first", "test", ("test",), first, timeout_seconds=2.0, max_retries=0)
    )
    orchestrator.register(
        ToolSpec("test_second", "test", ("test",), second, timeout_seconds=2.0, max_retries=0)
    )

    result = asyncio.run(orchestrator.execute(["test_first", "test_second"], message="test", context={}))

    assert list(result) == ["test_first", "test_second"]
    assert result["test_first"]["ok"] is True
    assert result["test_first"]["tool"] == "test_first"
    assert result["test_first"]["capabilities"] == ["test"]
    assert result["test_first"]["execution"]["attempt"] == 1
    assert result["test_second"]["evidence"] == "second"


def test_tool_timeout_is_bounded_and_reported():
    orchestrator = ToolOrchestrator()

    async def slow(**kwargs):
        await asyncio.sleep(0.05)
        return {"ok": True}

    orchestrator.register(
        ToolSpec("test_slow", "test", ("test",), slow, timeout_seconds=0.01, max_retries=0)
    )

    result = asyncio.run(orchestrator.execute(["test_slow"], message="test", context={}))

    assert result["test_slow"]["ok"] is False
    assert result["test_slow"]["error"] == "tool_timeout"


def test_agent_loop_replans_after_insufficient_tool_result():
    orchestrator = ToolOrchestrator()

    async def first(**kwargs):
        return {"ok": True, "evidence": "", "needs_more_evidence": True}

    async def second(**kwargs):
        return {"ok": True, "evidence": "replanned evidence"}

    orchestrator.register(
        ToolSpec("test_first_loop", "test", ("test",), first, timeout_seconds=2.0, max_retries=0)
    )
    orchestrator.register(
        ToolSpec("test_second_loop", "test", ("test",), second, timeout_seconds=2.0, max_retries=0)
    )

    orchestrator.cognitive_selection = lambda message, context: {
        "selected_tools": ["test_second_loop"]
    }

    result = asyncio.run(
        orchestrator.execute(
            ["test_first_loop"],
            message="test",
            context={"agent_loop": True, "max_tool_steps": 2},
        )
    )

    assert result["test_first_loop"]["needs_more_evidence"] is True
    assert result["test_second_loop"]["evidence"] == "replanned evidence"
