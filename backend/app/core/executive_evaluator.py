"""Executive post-generation contract owned by Bitey.

The evaluator validates the generated answer against the decision made by the
Brain. It is deterministic and provider-independent: models never decide
whether their own output is accepted.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ExecutiveEvaluation:
    decision: str
    passed: bool
    evidence_compliant: bool
    tool_compliant: bool
    risk_compliant: bool
    verification_compliant: bool
    provider_independent: bool
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExecutiveEvaluator:
    """Validate output against an already-issued Brain decision."""

    def evaluate(self, *, state: Any, answer: str, evidence: str = "", selected_tools: list[str] | None = None) -> ExecutiveEvaluation:
        tools = list(selected_tools or [])
        reasons: list[str] = []
        text = (answer or "").strip()

        evidence_required = bool(getattr(state, "evidence_required", False))
        evidence_ok = bool(evidence) if evidence_required else True
        if evidence_required and not evidence_ok:
            reasons.append("required_evidence_missing")

        required_tools = list(getattr(state, "tool_priority", []) or [])
        tool_ok = all(tool in tools for tool in required_tools)
        if required_tools and not tool_ok:
            reasons.append("required_tool_not_executed")

        risk = str(getattr(state, "risk_level", "low"))
        risk_ok = not (risk == "critical" and bool(getattr(state, "execution_allowed", False)))
        if not risk_ok:
            reasons.append("critical_risk_execution_policy_violation")

        verification_required = bool(getattr(state, "verification_required", False))
        verification_ok = not verification_required or bool(evidence) or "verif" in text.lower()
        if verification_required and not verification_ok:
            reasons.append("verification_requirement_not_satisfied")

        provider_independent = True
        if not text:
            reasons.append("empty_generation")

        passed = bool(text) and evidence_ok and tool_ok and risk_ok and verification_ok
        decision = "accept" if passed else "revise"
        return ExecutiveEvaluation(decision, passed, evidence_ok, tool_ok, risk_ok, verification_ok, provider_independent, reasons or ["executive_contract_satisfied"])
