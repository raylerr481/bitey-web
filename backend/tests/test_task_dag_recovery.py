from app.core.task_dag import TaskDAG, TaskNode
from app.core.task_dag_store import dag_from_task, persist_dag


def test_dag_snapshot_round_trip_preserves_completed_results():
    dag = TaskDAG([
        TaskNode("research", "bounded_research", status="completed", result={"evidence_context": "evidence"}, attempts=1),
        TaskNode("synthesize", "synthesize", ["research"]),
        TaskNode("artifact", "build_artifact", ["synthesize"]),
        TaskNode("evaluate", "evaluate_result", ["artifact"]),
    ])
    task = {"metadata": {"existing": True}}
    persist_dag(task, dag)
    restored = dag_from_task(task)
    assert restored is not None
    assert restored.get("research").status == "completed"
    assert restored.get("research").result["evidence_context"] == "evidence"
    assert restored.ready()[0].id == "synthesize"


def test_running_node_is_reset_for_safe_restart():
    dag = TaskDAG([
        TaskNode("research", "bounded_research", status="completed", attempts=1),
        TaskNode("synthesize", "synthesize", ["research"], status="running", attempts=1),
        TaskNode("evaluate", "evaluate_result", ["synthesize"]),
    ])
    task = {}
    persist_dag(task, dag)
    restored = dag_from_task(task)
    restored.reset_running()
    assert restored.get("synthesize").status == "pending"
    assert restored.ready()[0].id == "synthesize"
