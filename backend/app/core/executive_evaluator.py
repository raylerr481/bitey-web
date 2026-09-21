"""Executive post-generation contract owned by Bitey."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import re


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

    _SPECIALIZED_DRIFT_MARKERS = (
        "sbt",
        "smart money concepts",
        "bos/choch",
        "bos",
        "choch",
        "fvg",
        "order blocks",
        "order block",
        "backtest determinista",
        "backtest determinístico",
        "señal técnica",
        "señal de trading",
        "no se enviaron órdenes",
        "no se enviaron ordenes",
    )

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
        conflict_detected: bool = False,
    ) -> ExecutiveEvaluation:
        tools_known = selected_tools is not None
        tools = list(selected_tools or [])
        reasons: list[str] = []
        text = (answer or "").strip()
        lower_text = text.lower()
        task_class = str(self._get(state, "task_class", "general") or "general").lower()
        evidence_required = bool(self._get(state, "evidence_required", False))
        conceptual_fallback = bool(self._get(state, "conceptual_fallback", False))

        def evidence_has_provenance(value: str) -> bool:
            # Evidence must contain a traceable source marker, not merely a
            # model-written claim or search-engine discovery snippet.
            if not value.strip():
                return False
            markers = (
                ("SOURCE", "CONTENT"),
                ("SOURCE", "EVIDENCE"),
                ("WEATHER SOURCE", "OBSERVATION TIME"),
                ("SBT verified market analysis", "Source:"),
                ("Local deterministic calculation:", "="),
            )
            return any(
                all(marker.lower() in value.lower() for marker in pair)
                for pair in markers
            )

        evidence_ok = evidence_has_provenance(evidence) if evidence_required and not conceptual_fallback else True
        if evidence_required and not evidence and not conceptual_fallback:
            reasons.append("required_evidence_missing")
        elif evidence_required and not evidence_ok:
            reasons.append("evidence_provenance_missing")

        # When verified sources contain an explicit factual conflict, the
        # generated answer must acknowledge it rather than silently selecting
        # one source as authoritative.
        conflict_acknowledged = True
        if conflict_detected and evidence_required:
            conflict_acknowledged = any(
                marker in lower_text
                for marker in (
                    "fuentes difieren", "fuentes discrepan", "según la fuente",
                    "las fuentes", "discrepancia", "difieren", "discrepan",
                    "sources disagree", "sources differ", "according to the source",
                    "discrepancy", "conflicting sources",
                )
            )
            if not conflict_acknowledged:
                reasons.append("source_conflict_not_acknowledged")

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
        safe_risk_refusal = (
            risk == "critical"
            and not execution_allowed
            and any(
                term in lower_text
                for term in ("no se ejecut", "no ejecutar", "bloquead", "no puedo ejecutar", "cannot execute")
            )
        )
        verification_ok = safe_risk_refusal or (not verification_required or bool(evidence))
        if verification_required and not verification_ok:
            reasons.append("verification_requirement_not_satisfied")

        # A general question must not be allowed to masquerade as an SBT/trading
        # execution. Provider models are untrusted workers and can drift into a
        # specialized answer even when the cognitive router correctly selected
        # the general domain. Detect strong SBT fingerprints here so the gateway
        # can deterministically request a clean rewrite before public output.
        if task_class == "general":
            drift_markers = []
            for marker in self._SPECIALIZED_DRIFT_MARKERS:
                # Match single-word markers as words. Substring matching would
                # flag innocent text such as Spanish "ambos" because it contains
                # the trading marker "bos".
                pattern = rf"\b{re.escape(marker)}\b"
                if re.search(pattern, lower_text):
                    drift_markers.append(marker)
            if drift_markers:
                reasons.append("general_domain_specialized_module_drift")

        provider_independent = True
        if not text:
            reasons.append("empty_generation")
        passed = bool(text) and evidence_ok and tool_ok and risk_ok and verification_ok and conflict_acknowledged and "general_domain_specialized_module_drift" not in reasons
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
