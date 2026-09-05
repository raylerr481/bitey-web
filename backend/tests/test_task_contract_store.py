from app.core.task_contract import TaskContract
from app.core.task_contract_store import contract_from_task, persist_contract


def test_contract_round_trip_through_task_metadata():
    contract = TaskContract(
        task_id="task-1",
        prompt="investiga esto",
        capability="deep_research",
        budget={"paid_inference": False, "max_retries": 3},
        retry_count=1,
        plan=[{"step": "research"}],
    )
    task = {"id": "task-1", "prompt": contract.prompt, "capability": contract.capability, "metadata": {}}
    persist_contract(task, contract)
    restored = contract_from_task(task)
    assert restored.task_id == "task-1"
    assert restored.capability == "deep_research"
    assert restored.retry_count == 1
    assert restored.plan == [{"step": "research"}]
    assert restored.budget["paid_inference"] is False


def test_retry_count_is_recovered_from_persisted_contract():
    contract = TaskContract(
        task_id="task-2",
        prompt="crea un documento",
        capability="documents",
        budget={"paid_inference": False, "max_retries": 2},
        retry_count=2,
        status="needs_review",
        recovery_reason="runtime_requires_review",
    )
    task = {"id": "task-2", "prompt": contract.prompt, "capability": contract.capability, "metadata": {}}
    persist_contract(task, contract)
    restored = contract_from_task(task)
    assert restored.retry_count == 2
    assert restored.budget["max_retries"] == 2
    assert restored.status == "needs_review"
