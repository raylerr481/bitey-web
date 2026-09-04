from types import SimpleNamespace

from app.core.workspace_execution import WorkspaceExecutionService


def test_artifact_gate_requires_brain_authorization():
    state = SimpleNamespace(execution_allowed=False, risk_level="low")
    evaluation = SimpleNamespace(decision="accept")
    assert WorkspaceExecutionService._artifact_authorized(state, evaluation, "document") is False


def test_artifact_gate_rejects_high_risk_execution():
    state = SimpleNamespace(execution_allowed=True, risk_level="high")
    evaluation = SimpleNamespace(decision="accept")
    assert WorkspaceExecutionService._artifact_authorized(state, evaluation, "document") is False


def test_artifact_gate_accepts_safe_evaluated_result():
    state = SimpleNamespace(execution_allowed=True, risk_level="low")
    evaluation = SimpleNamespace(decision="accept")
    assert WorkspaceExecutionService._artifact_authorized(state, evaluation, "document") is True
