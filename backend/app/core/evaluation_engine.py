from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any

from .executive_evaluator import ExecutiveEvaluator


@dataclass(frozen=True)
class EvaluationResult:
    quality: float
    evidence_alignment: float
    safety_compliance: float
    contradiction_risk: float
    confidence: float
    decision: str
    reasons: list[str]
    executive: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvaluationEngine:
    """Deterministic post-generation evaluator owned by Bitey."""

    _RISK_WORDS = re.compile(r"\b(buy|sell|purchase|order|execute|live|real money|compra|vende|vender|orden|ejecuta|ejecutar|dinero real)\b", re.I)
    _UNCERTAINTY = re.compile(r"\b(no sé|no tengo|no puedo verificar|uncertain|unclear|não sei|não posso verificar)\b", re.I)

    def evaluate(self, *, user_message: str, answer: str, context: dict[str, Any] | None = None, evidence: str = "") -> EvaluationResult:
        context = context or {}
        text = (answer or "").strip()
        reasons: list[str] = []
        quality = 1.0
        evidence_alignment = 1.0
        safety = 1.0
        contradiction_risk = 0.0

        if not text:
            return EvaluationResult(0.0, 0.0, 0.0, 1.0, 0.0, "reject", ["empty_response"])
        if len(text) < 24:
            quality -= 0.25; reasons.append("response_too_short")
        if len(text) > 12000:
            quality -= 0.10; reasons.append("response_excessively_long")

        evidence_required = bool(context.get("evidence_required"))
        if evidence_required and not evidence:
            evidence_alignment = 0.35
            reasons.append("evidence_required_but_unavailable")
            if not self._UNCERTAINTY.search(text):
                contradiction_risk += 0.25
                reasons.append("missing_evidence_disclosure")
        elif evidence:
            evidence_alignment = 0.85 if len(text) >= 60 else 0.65

        domain = str((context.get("cognition") or {}).get("intention", {}).get("domain") or context.get("domain") or "general").lower()
        if domain == "trading" or any(k in user_message.lower() for k in ("trading", "forex", "mt5", "trader", "bolsa")):
            if self._RISK_WORDS.search(text):
                safety -= 0.55; reasons.append("trading_action_language_detected")
            if "live" in text.lower() and "disabled" not in text.lower() and "deshabil" not in text.lower() and "desactiv" not in text.lower():
                safety -= 0.20; reasons.append("live_trading_not_explicitly_guarded")

        if any(word in text.lower() for word in ("siempre", "garantizado", "guaranteed", "sem risco", "sin riesgo")):
            contradiction_risk += 0.20; reasons.append("overconfident_claim")

        quality = max(0.0, min(1.0, quality)); safety = max(0.0, min(1.0, safety)); contradiction_risk = max(0.0, min(1.0, contradiction_risk))
        confidence = max(0.0, min(1.0, quality * 0.4 + evidence_alignment * 0.25 + safety * 0.25 + (1.0 - contradiction_risk) * 0.10))

        if safety < 0.60:
            decision = "reject"
        elif evidence_required and evidence_alignment < 0.50:
            decision = "revise"
        elif confidence < 0.60:
            decision = "revise"
        else:
            decision = "accept"

        brain_state = context.get("bitey_brain") or context.get("_bitey_brain_state")
        # Missing selected_tools means the evaluator cannot know whether tools
        # were executed. An explicit empty list means Bitey knows that none ran.
        selected_tools = context.get("selected_tools") if "selected_tools" in context else None
        if selected_tools is None and "tools_selected" in context:
            selected_tools = context.get("tools_selected")
        executive = ExecutiveEvaluator().evaluate(state=brain_state or {}, answer=text, evidence=evidence, selected_tools=selected_tools).as_dict()
        if not executive["passed"]:
            reasons.extend(f"executive:{reason}" for reason in executive["reasons"])
            if executive["risk_compliant"] is False:
                decision = "reject"
            elif decision != "reject":
                decision = "revise"

        if not reasons:
            reasons.append("response_passed_structural_policy_checks")
        return EvaluationResult(quality, evidence_alignment, safety, contradiction_risk, confidence, decision, reasons, executive)
