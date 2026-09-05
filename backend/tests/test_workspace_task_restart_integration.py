import pytest

from app.core.artifact_pipeline import build_artifact
from app.core.evaluation_engine import EvaluationResult
from app.core.task_dag import TaskDAG, TaskNode
from app.core.task_dag_store import dag_from_task, persist_dag
from app.core.workspace_execution import WorkspaceExecutionService


class ResumeProviders:
    def __init__(self):
        self.calls = 0

    async def generate(self, *, messages, context):
        self.calls += 1
        return "Síntesis recuperada desde el contexto persistido y lista para generar el documento final."


class MustNotResearch:
    def __init__(self):
        self.calls = 0

    async def run(self, query, context):
        self.calls += 1
        raise AssertionError("research_must_not_rerun_after_restart")


class AcceptEvaluator:
    def evaluate(self, **kwargs):
        return EvaluationResult(0.95, 0.95, 1.0, 0.0, 0.96, "accept", ["restart_recovery_test"])


@pytest.mark.asyncio
async def test_workspace_task_metadata_restart_resumes_last_valid_node():
    # This dict represents the row already stored in workspace_tasks.metadata.
    workspace_task = {
        "id": "task-restart-1",
        "workspace_id": "workspace-1",
        "metadata": {},
    }
    interrupted = TaskDAG([
        TaskNode(
            "research",
            "bounded_research",
            status="completed",
            result={"evidence_context": "Persisted evidence from research."},
            attempts=1,
        ),
        TaskNode(
            "synthesize",
            "compare_and_synthesize",
            ["research"],
            status="running",
            attempts=1,
        ),
        TaskNode("artifact", "build_artifact", ["synthesize"]),
        TaskNode("evaluate", "evaluate_result", ["artifact"]),
    ])
    persist_dag(workspace_task, interrupted)

    # Simulate process death: only the serialized workspace_tasks row survives.
    persisted_metadata = dict(workspace_task["metadata"])
    restarted_row = {
        "id": workspace_task["id"],
        "workspace_id": workspace_task["workspace_id"],
        "metadata": persisted_metadata,
    }

    restored = dag_from_task(restarted_row)
    assert restored is not None
    restored.reset_running()
    assert restored.get("research").status == "completed"
    assert restored.get("synthesize").status == "pending"
    assert restored.ready()[0].id == "synthesize"

    service = WorkspaceExecutionService()
    service.providers = ResumeProviders()
    service.research = MustNotResearch()
    service.evaluator = AcceptEvaluator()

    checkpoints = []

    async def checkpoint(dag):
        # Simulates the workspace_tasks.metadata write performed at each runtime checkpoint.
        persist_dag(restarted_row, dag)
        checkpoints.append(dag.to_dict())

    result = await service.execute(
        prompt="Investiga, compara y crea un documento sobre el tema",
        capability="documents",
        context={
            "workspace_id": restarted_row["workspace_id"],
            "task_id": restarted_row["id"],
            "metadata": restarted_row["metadata"],
            "_persist_dag": checkpoint,
        },
    )

    assert result["status"] == "completed"
    assert result["cognitive_decision"]["resumed"] is True
    assert result["artifact"]["status"] == "ready"
    assert result["evaluation"]["decision"] == "accept"
    assert service.research.calls == 0
    assert service.providers.calls == 1

    final_dag = dag_from_task(restarted_row)
    assert final_dag is not None
    assert final_dag.is_complete()
    assert [node.status for node in final_dag.nodes] == ["completed"] * 4
    assert final_dag.get("research").attempts == 1
    assert final_dag.get("synthesize").attempts == 2
    assert checkpoints
