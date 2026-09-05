from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


TASK_STATUSES = {"pending", "planning", "researching", "generating", "evaluating", "needs_review", "completed", "failed"}


@dataclass
class TaskContract:
    """Single bounded contract shared by cognition, execution, evaluation and artifacts."""

    task_id: str = field(default_factory=lambda: str(uuid4()))
    prompt: str = ""
    intent: str = "conversation"
    capability: str = "chat"
    constraints: list[str] = field(default_factory=list)
    risk_level: str = "low"
    budget: dict[str, Any] = field(default_factory=lambda: {"paid_inference": False, "max_retries": 2})
    plan: list[dict[str, Any]] = field(default_factory=list)
    selected_tools: list[str] = field(default_factory=list)
    selected_models: list[str] = field(default_factory=list)
    evidence_policy: dict[str, Any] = field(default_factory=dict)
    evaluation_policy: dict[str, Any] = field(default_factory=lambda: {"required": True})
    artifact_contract: dict[str, Any] | None = None
    authorization: dict[str, Any] = field(default_factory=lambda: {"side_effects": False})
    status: str = "pending"
    retry_count: int = 0
    recovery_reason: str | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.prompt.strip():
            raise ValueError("task_prompt_required")
        if self.status not in TASK_STATUSES:
            raise ValueError("invalid_task_status")
        if int(self.budget.get("max_retries", 2)) < 0:
            raise ValueError("invalid_retry_budget")
        if self.budget.get("paid_inference") is not False:
            raise ValueError("paid_inference_forbidden")
        if self.retry_count > int(self.budget.get("max_retries", 2)):
            raise ValueError("retry_budget_exhausted")

    def transition(self, status: str, *, reason: str | None = None) -> None:
        if status not in TASK_STATUSES:
            raise ValueError("invalid_task_status")
        self.status = status
        self.recovery_reason = reason
        self.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "intent": self.intent,
            "capability": self.capability,
            "constraints": list(self.constraints),
            "risk_level": self.risk_level,
            "budget": dict(self.budget),
            "plan": list(self.plan),
            "selected_tools": list(self.selected_tools),
            "selected_models": list(self.selected_models),
            "evidence_policy": dict(self.evidence_policy),
            "evaluation_policy": dict(self.evaluation_policy),
            "artifact_contract": self.artifact_contract,
            "authorization": dict(self.authorization),
            "status": self.status,
            "retry_count": self.retry_count,
            "recovery_reason": self.recovery_reason,
        }
