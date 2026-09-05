import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from app.background_worker import recover_stale_workspace_tasks

class TestWorkspaceTaskAutoRecovery(unittest.TestCase):
    def test_stale_running_task_is_requeued_once_and_recovered(self):
        old=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
        task={"id":"task-1","workspace_id":"ws-1","status":"running","updated_at":old,"execution_token":"dead-process-token","metadata":{"task_dag":{"version":1,"nodes":[{"id":"research","action":"worker","status":"completed","result":{"ok":True},"attempts":1},{"id":"synthesize","action":"synthesize","depends_on":["research"],"status":"running","attempts":1}]}}}
        class FakeResponse:
            def __init__(self,payload): self.payload=payload
            def raise_for_status(self): return None
            def json(self): return self.payload
        class FakeClient:
            async def __aenter__(self): return self
            async def __aexit__(self,*args): return False
            async def get(self,*args,**kwargs): return FakeResponse([task])
            async def patch(self,*args,**kwargs): task.update(kwargs["json"]); return FakeResponse([dict(task)])
        async def fake_execute(workspace_id,task_id,recovered): return dict(recovered)
        with patch("app.background_worker.SUPABASE_URL","https://example.supabase.co"), patch("app.background_worker.SUPABASE_KEY","test-key"), patch("app.background_worker.httpx.AsyncClient",return_value=FakeClient()), patch("app.workspace_api._execute_task",new=AsyncMock(side_effect=fake_execute)) as execute:
            result=asyncio.run(recover_stale_workspace_tasks(stale_seconds=60))
        self.assertEqual(result,{"scanned":1,"recovered":1,"skipped":0}); execute.assert_awaited_once(); recovered=execute.await_args.args[2]
        self.assertEqual(recovered["status"],"queued"); self.assertIsNone(recovered["execution_token"]); self.assertEqual(recovered["metadata"]["recovery"]["reason"],"stale_running_task")
    def test_fresh_running_task_is_not_recovered(self):
        fresh=datetime.now(timezone.utc).isoformat(); task={"id":"task-2","workspace_id":"ws-1","status":"running","updated_at":fresh,"metadata":{"task_dag":{"version":1,"nodes":[]}}}
        class FakeResponse:
            def raise_for_status(self): return None
            def json(self): return [task]
        class FakeClient:
            async def __aenter__(self): return self
            async def __aexit__(self,*args): return False
            async def get(self,*args,**kwargs): return FakeResponse()
            async def patch(self,*args,**kwargs): raise AssertionError("fresh_task_must_not_patch")
        with patch("app.background_worker.SUPABASE_URL","https://example.supabase.co"), patch("app.background_worker.SUPABASE_KEY","test-key"), patch("app.background_worker.httpx.AsyncClient",return_value=FakeClient()), patch("app.workspace_api._execute_task",new=AsyncMock()) as execute:
            result=asyncio.run(recover_stale_workspace_tasks(stale_seconds=300))
        self.assertEqual(result,{"scanned":1,"recovered":0,"skipped":1}); execute.assert_not_awaited()
if __name__=="__main__": unittest.main()
