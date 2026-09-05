import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.workspace_api import recover_stale_workspace_tasks


class TestWorkspaceTaskAutoRecovery(unittest.TestCase):
    def test_stale_running_task_is_requeued_once_and_recovered(self):
        old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        task = {
            "id": "task-1",
            "workspace_id": "ws-1",
            "status": "running",
            "updated_at": old,
            "execution_token": "dead-process-token",
            "metadata": {
                "task_dag": {
                    "version": 1,
                    "max_nodes": 12,
                    "max_depth": 6,
                    "nodes": [
                        {"id": "research", "action": "bounded_research", "depends_on": [], "status": "completed", "result": {"ok": True}, "attempts": 1},
                        {"id": "synthesize", "action": "synthesize", "depends_on": ["research"], "status": "running", "result": None, "attempts": 1},
                    ],
                }
            },
        }

        async def fake_db(method, table, **kwargs):
            if method == "GET":
                return [task]
            if method == "PATCH":
                filters = kwargs.get("params", {})
                if filters.get("status") == "eq.running" and filters.get("updated_at") == f"eq.{old}":
                    task.update(kwargs["json"])
                    return [dict(task)]
                return []
            raise AssertionError(method)

        async def fake_execute(workspace_id, task_id, recovered):
            recovered["status"] = "completed"
            return recovered

        with patch("app.workspace_api._db", new=AsyncMock(side_effect=fake_db)), patch(
            "app.workspace_api._execute_task", new=AsyncMock(side_effect=fake_execute)
        ) as execute:
            result = asyncio.run(recover_stale_workspace_tasks(stale_seconds=60))

        self.assertEqual(result["recovered"], 1)
        self.assertEqual(result["skipped"], 0)
        execute.assert_awaited_once()
        recovered = execute.await_args.args[2]
        self.assertEqual(recovered["status"], "queued")
        self.assertIsNone(recovered["execution_token"])
        self.assertEqual(recovered["metadata"]["recovery"]["reason"], "stale_running_task")

    def test_fresh_running_task_is_not_recovered(self):
        fresh = datetime.now(timezone.utc).isoformat()
        task = {
            "id": "task-2",
            "workspace_id": "ws-1",
            "status": "running",
            "updated_at": fresh,
            "metadata": {"task_dag": {"version": 1, "nodes": []}},
        }

        async def fake_db(method, table, **kwargs):
            return [task] if method == "GET" else []

        with patch("app.workspace_api._db", new=AsyncMock(side_effect=fake_db)), patch(
            "app.workspace_api._execute_task", new=AsyncMock()
        ) as execute:
            result = asyncio.run(recover_stale_workspace_tasks(stale_seconds=300))

        self.assertEqual(result["recovered"], 0)
        self.assertEqual(result["skipped"], 1)
        execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
