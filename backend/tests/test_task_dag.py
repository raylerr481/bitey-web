import pytest

from app.core.task_dag import TaskDAG, TaskNode, dag_from_plan


def test_dag_orders_ready_nodes_and_dependencies():
    dag = TaskDAG(nodes=[TaskNode("research", "research"), TaskNode("write", "write", ["research"])])
    dag.validate()
    assert [n.id for n in dag.ready()] == ["research"]
    dag.mark_completed("research", "evidence")
    assert [n.id for n in dag.ready()] == ["write"]


def test_dag_rejects_cycles():
    dag = TaskDAG(nodes=[TaskNode("a", "a", ["b"]), TaskNode("b", "b", ["a"])])
    with pytest.raises(ValueError, match="cycle"):
        dag.validate()


def test_plan_is_bounded():
    dag = dag_from_plan([{"action": f"step-{i}"} for i in range(20)])
    assert len(dag.nodes) <= 12
