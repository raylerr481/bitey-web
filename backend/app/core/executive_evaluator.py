"""Executive post-generation contract owned by Bitey."""
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
    """Validate generated output against Bitey's already-issued decision."""

    @staticmethod
    def _get(state: Any, key: str, default: Any = None) -> Any:
        if isinstance(state, dict):
            return state.get(key, default)
        return getattr(state, key, default)

    def evaluate(
        self,
        *,
        state: Any,
        answer: str,
        evidence: str = "",
        selected_tools: list[str] | None = None,
    ) -> ExecutiveEvaluation:
        tools_known = selected_tools is not None
        tools = list(selected_tools or [])
        reasons: list[str] = []
        text = (answer or "").strip()

        evidence_required = bool(self._get(state, "evidence_required", False))
        evidence_ok = bool(evidence) if evidence_required else True
        if evidence_required and not evidence_ok:
            reasons.append("required_evidence_missing")

        required_tools = list(self._get(state, "tool_priority", []) or [])
        tool_ok = True if not tools_known else all(tool in tools for tool in required_tools)
        if tools_known and required_tools and not tool_ok:
            reasons.append("required_tool_not_executed")

        risk = str(self._get(state, "risk_level", "low"))
        execution_allowed = bool(self._get(state, "execution_allowed", False))
        risk_ok = not (risk == "critical" and execution_allowed)
        if not risk_ok:
            reasons.append("critical_risk_execution_policy_violation")

        verification_required = bool(self._get(state, "verification_required", False))
        verification_ok = not verification_required or bool(evidence)
        if verification_required and not verification_ok:
            reasons.append("verification_requirement_not_satisfied")

        provider_independent = True
        if not text:
            reasons.append("empty_generation")

        passed = bool(text) and evidence_ok and tool_ok and risk_ok and verification_ok
        decision = "accept" if passed else "revise"
        return ExecutiveEvaluation(
            decision=decision,
            passed=passed,
            evidence_compliant=evidence_ok,
            tool_compliant=tool_ok,
            risk_compliant=risk_ok,
            verification_compliant=verification_ok,
            provider_independent=provider_independent,
            reasons=reasons or ["executive_contract_satisfied"],
        )
