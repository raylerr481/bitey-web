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


def verify_answer_claims(
    answer: str,
    evidence: str = "",
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Conservative final-answer verification against retrieved evidence."""
    text = (answer or "").strip()
    sources = sources or []
    if not evidence:
        return {
            "valid": True,
            "claim_count": 0,
            "supported_count": 0,
            "unsupported_count": 0,
            "uncited_count": 0,
            "issues": [],
            "reason": "no_research_evidence",
        }

    stop = {
        "the","and","for","with","that","this","from","were","have","has","had","was","are","is",
        "not","did","does","their","they","there","into","about","than","then","also","after","before",
        "more","less","very","only","its","his","her","our","you","your","what","when","where","which",
        "de","la","el","los","las","que","con","por","para","una","un","del","se","en","es","como","más",
        "menos","sobre","esta","este","estas","estos","dos","tres","una",
    }
    def tokens(value: str) -> set[str]:
        words = re.findall(r"[A-Za-zÀ-ÿ0-9]{3,}", value.lower())
        return {w for w in words if w not in stop and not w.startswith("s") or (w.startswith("s") and w[1:].isdigit())}

    raw_claims = re.split(r"(?<=[.!?])\s+|\n+", text)
    claims = []
    for claim in raw_claims:
        claim = re.sub(r"\s+", " ", claim).strip(" -•")
        if len(claim) < 25 or claim.endswith("?"):
            continue
        if claim.startswith(("*", "#")):
            claim = claim.lstrip("*# ")
        claims.append(claim)

    source_blocks = re.split(r"(?=SOURCE\s*\d+)", evidence, flags=re.I)
    indexed = {}
    for block in source_blocks:
        match = re.search(r"SOURCE\s*(\d+)", block, re.I)
        if match:
            indexed[int(match.group(1))] = block

    supported = 0
    unsupported = 0
    uncited = 0
    issues = []
    for claim in claims[:30]:
        citation_ids = [int(x) for x in re.findall(r"\[S(\d+)\]", claim)]
        clean_claim = re.sub(r"\[S\d+\]", " ", claim)
        claim_tokens = tokens(clean_claim)
        numbers = set(re.findall(r"(?<![\w])(?:20\d{2}|\d+(?:[.,]\d+)?%?)(?![\w])", clean_claim))
        candidates = [(sid, indexed[sid]) for sid in citation_ids if sid in indexed] if citation_ids else list(indexed.items())
        if citation_ids and not candidates:
            unsupported += 1
            issues.append({"claim": claim[:260], "reason": "invalid_source_citation"})
            continue
        if not citation_ids:
            uncited += 1

        best_overlap = 0.0
        best_numbers = False
        best_sid = None
        for sid, block in candidates:
            block_tokens = tokens(block)
            overlap = len(claim_tokens & block_tokens) / max(1, len(claim_tokens))
            block_numbers = set(re.findall(r"(?<![\w])(?:20\d{2}|\d+(?:[.,]\d+)?%?)(?![\w])", block))
            number_ok = not numbers or numbers.issubset(block_numbers)
            score = overlap + (0.20 if number_ok else -0.20)
            if score > best_overlap:
                best_overlap, best_sid = score, sid
                best_numbers = number_ok

        if best_overlap >= 0.48 and best_numbers:
            supported += 1
        else:
            unsupported += 1
            issues.append({
                "claim": claim[:260],
                "reason": "insufficient_evidence_support",
                "source": best_sid,
            })

    total = len(claims)
    return {
        "valid": unsupported == 0,
        "claim_count": total,
        "supported_count": supported,
        "unsupported_count": unsupported,
        "uncited_count": uncited,
        "issues": issues[:8],
        "reason": "claims_checked",
    }


class EvaluationEngine:
    """Deterministic post-generation evaluator owned by Bitey."""

    _RISK_WORDS = re.compile(r"\b(buy|sell|purchase|order|execute|live|real money|compra|vende|vender|orden|ejecuta|ejecutar|dinero real)\b", re.I)
    _UNCERTAINTY = re.compile(r"\b(no sé|no tengo|no puedo verificar|uncertain|unclear|não sei|não posso verificar)\b", re.I)
    _CONVERSATIONAL_INTENTS = {"greeting", "self_identity", "small_talk", "acknowledgement"}

    def evaluate(self, *, user_message: str, answer: str, context: dict[str, Any] | None = None, evidence: str = "", conflict_detected: bool = False) -> EvaluationResult:
        context = context or {}
        text = (answer or "").strip()
        reasons: list[str] = []
        quality = 1.0
        evidence_alignment = 1.0
        safety = 1.0
        contradiction_risk = 0.0

        if not text:
            return EvaluationResult(0.0, 0.0, 0.0, 1.0, 0.0, "reject", ["empty_response"])

        cognition = context.get("cognition") or {}
        intention = cognition.get("intention") or {}
        intent = str(intention.get("intent") or context.get("intent") or "").lower()
        domain = str(intention.get("domain") or context.get("domain") or "general").lower()
        conversational = intent in self._CONVERSATIONAL_INTENTS and domain == "general"
        # Conceptual general-knowledge questions do not require a minimum answer
        # length. Evidence requirements are enforced independently by the executive brain.
        conceptual = bool(re.search(
            r"\b(?:qu[eé]\s+es|qu[eé]\s+son|qu[eé]\s+significa|definici[oó]n|define|explica|concepto|what\s+is|what\s+are|how\s+does)\b",
            user_message,
            re.I,
        )) and domain == "general"

        # Short answers are valid for greetings and conceptual general questions.
        if len(text) < 24 and not conversational and not conceptual:
            quality -= 0.25
            reasons.append("response_too_short")
        if len(text) > 12000:
            quality -= 0.10
            reasons.append("response_excessively_long")

        evidence_required = bool(context.get("evidence_required"))
        if evidence_required and not evidence:
            evidence_alignment = 0.35
            reasons.append("evidence_required_but_unavailable")
            if not self._UNCERTAINTY.search(text):
                contradiction_risk += 0.25
                reasons.append("missing_evidence_disclosure")
        elif evidence:
            evidence_alignment = 0.85 if len(text) >= 60 else 0.65

        if domain == "trading" or any(k in user_message.lower() for k in ("trading", "forex", "mt5", "trader", "bolsa")):
            if self._RISK_WORDS.search(text):
                safety -= 0.55
                reasons.append("trading_action_language_detected")
            if "live" in text.lower() and "disabled" not in text.lower() and "deshabil" not in text.lower() and "desactiv" not in text.lower():
                safety -= 0.20
                reasons.append("live_trading_not_explicitly_guarded")

        if any(word in text.lower() for word in ("siempre", "garantizado", "guaranteed", "sem risco", "sin riesgo")):
            contradiction_risk += 0.20
            reasons.append("overconfident_claim")

        quality = max(0.0, min(1.0, quality))
        safety = max(0.0, min(1.0, safety))
        contradiction_risk = max(0.0, min(1.0, contradiction_risk))
        confidence = max(0.0, min(1.0, quality * 0.4 + evidence_alignment * 0.25 + safety * 0.25 + (1.0 - contradiction_risk) * 0.10))

        if safety < 0.60:
            decision = "reject"
        elif evidence_required and evidence_alignment < 0.50:
            decision = "revise"
        elif confidence < 0.60:
            decision = "revise"
        else:
            decision = "accept"

        answer_verification = context.get("answer_verification") or {}
        if evidence and int(answer_verification.get("unsupported_count", 0) or 0) > 0:
            evidence_alignment = min(evidence_alignment, 0.45)
            reasons.append("unsupported_answer_claims")

        brain_state = context.get("bitey_brain") or context.get("_bitey_brain_state")
        selected_tools = context.get("selected_tools") if "selected_tools" in context else None
        if selected_tools is None and "tools_selected" in context:
            selected_tools = context.get("tools_selected")
        executive = ExecutiveEvaluator().evaluate(state=brain_state or {}, answer=text, evidence=evidence, selected_tools=selected_tools, conflict_detected=conflict_detected).as_dict()
        if not executive["passed"]:
            reasons.extend(f"executive:{reason}" for reason in executive["reasons"])
            if executive["risk_compliant"] is False:
                decision = "reject"
            elif decision != "reject":
                decision = "revise"

        if not reasons:
            reasons.append("response_passed_structural_policy_checks")
        return EvaluationResult(quality, evidence_alignment, safety, contradiction_risk, confidence, decision, reasons, executive)
