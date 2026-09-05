import pytest

from app.core.task_contract import TaskContract


def test_contract_defaults_to_no_paid_inference():
    contract = TaskContract(prompt="prepara un documento")
    assert contract.budget["paid_inference"] is False
    assert contract.status == "pending"


def test_contract_rejects_paid_inference():
    with pytest.raises(ValueError, match="paid_inference_forbidden"):
        TaskContract(prompt="hola", budget={"paid_inference": True, "max_retries": 2})


def test_contract_rejects_retry_over_budget():
    with pytest.raises(ValueError, match="retry_budget_exhausted"):
        TaskContract(prompt="hola", retry_count=3, budget={"paid_inference": False, "max_retries": 2})


def test_contract_transition_is_bounded():
    contract = TaskContract(prompt="investiga", budget={"paid_inference": False, "max_retries": 2})
    contract.transition("researching")
    contract.transition("evaluating")
    assert contract.status == "evaluating"
