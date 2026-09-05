from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


MAX_NODES = 12
MAX_DEPTH = 6


@dataclass
class TaskNode:
    id: str
    action: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"
    result: Any = None


@dataclass
class TaskDAG:
    """Bounded dependency graph for long-horizon Bitey tasks."""
    nodes: list[TaskNode] = field(default_factory=list)
    max_nodes: int = MAX_NODES
    max_depth: int = MAX_DEPTH

    def validate(self) -> None:
        if not self.nodes:
            return
        if len(self.nodes) > self.max_nodes:
            raise ValueError("task_dag_node_limit_exceeded")
        ids = {node.id for node in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("task_dag_duplicate_node")
        for node in self.nodes:
            if any(dep not in ids for dep in node.depends_on):
                raise ValueError("task_dag_unknown_dependency")
            if node.id in node.depends_on:
                raise ValueError("task_dag_self_dependency")
        self._assert_acyclic()
        if self.depth() > self.max_depth:
            raise ValueError("task_dag_depth_limit_exceeded")

    def _assert_acyclic(self) -> None:
        graph = {node.id: node.depends_on for node in self.nodes}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("task_dag_cycle_detected")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dep in graph[node_id]:
                visit(dep)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in graph:
            visit(node_id)

    def depth(self) -> int:
        graph = {node.id: node.depends_on for node in self.nodes}
        memo: dict[str, int] = {}

        def level(node_id: str) -> int:
            if node_id in memo:
                return memo[node_id]
            deps = graph[node_id]
            memo[node_id] = 1 + max((level(dep) for dep in deps), default=0)
            return memo[node_id]

        return max((level(node_id) for node_id in graph), default=0)

    def ready(self) -> list[TaskNode]:
        completed = {n.id for n in self.nodes if n.status == "completed"}
        return [n for n in self.nodes if n.status == "pending" and all(dep in completed for dep in n.depends_on)]

    def mark_completed(self, node_id: str, result: Any = None) -> None:
        for node in self.nodes:
            if node.id == node_id:
                node.status = "completed"
                node.result = result
                self.validate()
                return
        raise ValueError("task_dag_unknown_node")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"max_nodes": self.max_nodes, "max_depth": self.max_depth, "nodes": [{"id": n.id, "action": n.action, "depends_on": list(n.depends_on), "status": n.status, "result": n.result} for n in self.nodes]}


def dag_from_plan(plan: list[dict[str, Any]]) -> TaskDAG:
    nodes: list[TaskNode] = []
    previous: str | None = None
    for index, step in enumerate(plan[:MAX_NODES], start=1):
        node_id = str(step.get("id") or f"step-{index}")
        deps = list(step.get("depends_on") or ([] if previous is None else [previous]))
        nodes.append(TaskNode(id=node_id, action=str(step.get("action") or "worker"), depends_on=deps))
        previous = node_id
    dag = TaskDAG(nodes=nodes)
    dag.validate()
    return dag
