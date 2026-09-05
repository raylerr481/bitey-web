from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


MAX_NODES = 12
MAX_DEPTH = 6
NODE_STATUSES = {"pending", "running", "completed", "failed"}


@dataclass
class TaskNode:
    id: str
    action: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    attempts: int = 0


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
            if node.status not in NODE_STATUSES:
                raise ValueError("task_dag_invalid_node_status")
            if node.attempts < 0:
                raise ValueError("task_dag_invalid_attempts")
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

    def mark_running(self, node_id: str) -> TaskNode:
        node = self.get(node_id)
        if node.status != "pending":
            raise ValueError("task_dag_node_not_pending")
        node.status = "running"
        node.attempts += 1
        self.validate()
        return node

    def mark_completed(self, node_id: str, result: Any = None) -> None:
        node = self.get(node_id)
        node.status = "completed"
        node.result = result
        self.validate()

    def mark_failed(self, node_id: str, result: Any = None) -> None:
        node = self.get(node_id)
        node.status = "failed"
        node.result = result
        self.validate()

    def reset_running(self) -> list[str]:
        """Make an interrupted in-flight node resumable after process restart."""
        reset: list[str] = []
        for node in self.nodes:
            if node.status == "running":
                node.status = "pending"
                reset.append(node.id)
        self.validate()
        return reset

    def get(self, node_id: str) -> TaskNode:
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise ValueError("task_dag_unknown_node")

    def is_complete(self) -> bool:
        return bool(self.nodes) and all(node.status == "completed" for node in self.nodes)

    def is_deadlocked(self) -> bool:
        return bool(self.nodes) and not self.is_complete() and not self.ready() and not any(node.status == "running" for node in self.nodes)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskDAG":
        if not isinstance(data, dict):
            raise ValueError("task_dag_invalid_snapshot")
        nodes = [
            TaskNode(
                id=str(item.get("id")),
                action=str(item.get("action") or "worker"),
                depends_on=[str(dep) for dep in (item.get("depends_on") or [])],
                status=str(item.get("status") or "pending"),
                result=item.get("result"),
                attempts=int(item.get("attempts") or 0),
            )
            for item in (data.get("nodes") or [])
        ]
        dag = cls(nodes=nodes, max_nodes=int(data.get("max_nodes", MAX_NODES)), max_depth=int(data.get("max_depth", MAX_DEPTH)))
        dag.validate()
        return dag

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"version": 1, "max_nodes": self.max_nodes, "max_depth": self.max_depth, "nodes": [{"id": n.id, "action": n.action, "depends_on": list(n.depends_on), "status": n.status, "result": n.result, "attempts": n.attempts} for n in self.nodes]}


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
