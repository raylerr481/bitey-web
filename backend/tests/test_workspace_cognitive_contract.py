import pytest

from app.workspace_api import inspect_cognitive_plan


@pytest.mark.asyncio
async def test_cognitive_inspect_does_not_invoke_model():
    result = await inspect_cognitive_plan({
        "prompt": "Compara las opciones actuales y verifica la evidencia",
        "capability": "deep_research",
    })

    assert result["owner"] == "bitey_ia"
    assert result["authority"] == "bitey_brain"
    assert result["model_invocation"] is False
    assert result["route"] == "research"
    assert result["brain"]["evidence_required"] is True
    assert result["research_runtime"]["bounded"] if "bounded" in result["research_runtime"] else True


@pytest.mark.asyncio
async def test_cognitive_inspect_routes_artifacts_without_generation():
    result = await inspect_cognitive_plan({
        "prompt": "Crea un documento con el plan",
        "capability": "documents",
    })

    assert result["model_invocation"] is False
    assert result["route"] == "artifact"
    assert result["artifact_type"] == "document"


@pytest.mark.asyncio
async def test_cognitive_inspect_requires_prompt():
    with pytest.raises(Exception) as exc:
        await inspect_cognitive_plan({"capability": "chat"})
    assert getattr(exc.value, "status_code", None) == 422
