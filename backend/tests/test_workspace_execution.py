import pytest

from app.core.evaluation_engine import EvaluationResult
from app.core.workspace_execution import WorkspaceExecutionService


class FakeProviders:
    async def generate(self, *, messages, context):
        return "Resultado suficientemente completo para superar la evaluación estructural de Bitey."


class FakeResearchResult:
    evidence_context = "Fuente oficial: evidencia de prueba."
    decision = {"reasoning_mode": "evidence_first", "evidence_required": True}

    def as_dict(self):
        return {
            "original_query": "investiga el tema",
            "steps": [{"index": 1, "query": "investiga el tema", "status": "completed", "sources": [], "evidence": "Fuente oficial: evidencia de prueba."}],
            "evidence_context": self.evidence_context,
            "decision": self.decision,
            "bounded": True,
        }


class FakeResearch:
    async def run(self, query, context):
        return FakeResearchResult()


class FakeEvaluator:
    def evaluate(self, **kwargs):
        return EvaluationResult(0.9, 0.9, 1.0, 0.0, 0.93, "accept", ["test_accept"])


@pytest.mark.asyncio
async def test_artifact_capability_runs_full_pipeline():
    service = WorkspaceExecutionService()
    service.providers = FakeProviders()
    service.research = FakeResearch()
    service.evaluator = FakeEvaluator()
    result = await service.execute(prompt="Crea un documento sobre el tema", capability="documents", context={"workspace_id":"w1","task_id":"t1"})
    assert result["status"] == "completed"
    assert result["artifact"]["artifact_type"] == "document"
    assert result["artifact"]["status"] == "ready"
    assert result["evaluation"]["decision"] == "accept"


@pytest.mark.asyncio
async def test_research_capability_remains_bounded_and_returns_evidence():
    service = WorkspaceExecutionService()
    service.providers = FakeProviders()
    service.research = FakeResearch()
    service.evaluator = FakeEvaluator()
    result = await service.execute(prompt="Investiga el tema", capability="deep_research", context={"workspace_id":"w1","task_id":"t2"})
    assert result["research"]["bounded"] is True
    assert result["research"]["evidence_context"]
    assert len(result["research"]["steps"]) <= 4
