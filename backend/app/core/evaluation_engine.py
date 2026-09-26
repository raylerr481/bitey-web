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
    query: str = "",
) -> dict[str, Any]:
    """Conservative final-answer verification with atomic claim-level support."""
    text = (answer or "").strip()
    sources = sources or []
    if not evidence:
        return {
            "valid": True,
            "claim_count": 0,
            "supported_count": 0,
            "unsupported_count": 0,
            "partial_count": 0,
            "uncited_count": 0,
            "issues": [],
            "claim_details": [],
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
        return {w for w in words if w not in stop}

    raw_claims = re.split(r"(?<=[.!?])\s+|\n+", text)
    claims: list[str] = []
    skipped = 0
    meta_re = re.compile(
        r"^(?:aquí|en resumen|en otras palabras|por tanto|por eso|mi respuesta|"
        r"the answer|in summary|in other words|therefore|my answer|"
        r"puedo ayudarte|puedo explicarte|let me explain|i can help)\b",
        re.I,
    )
    inference_re = re.compile(
        r"\b(?:esto sugiere|esto indica|parece que|podría significar|es probable que|"
        r"esto implica|in other words|this suggests|this indicates|it appears|"
        r"may mean|likely means|this implies)\b",
        re.I,
    )
    for claim in raw_claims:
        claim = re.sub(r"\s+", " ", claim).strip(" -•")
        if len(claim) < 25 or claim.endswith("?"):
            continue
        if claim.startswith(("*", "#")):
            claim = claim.lstrip("*# ")
        if meta_re.search(claim) and not re.search(r"\b(?:es|son|fue|será|is|are|was|will)\b", claim, re.I):
            skipped += 1
            continue
        if inference_re.search(claim) and not re.search(r"\[S\d+\]", claim):
            skipped += 1
            continue
        claims.append(claim)

    source_blocks = re.split(r"(?=SOURCE\s*\d+)", evidence, flags=re.I)
    indexed: dict[int, str] = {}
    query_tokens = tokens(query)
    source_relevance: dict[int, float] = {}
    for block in source_blocks:
        match = re.search(r"SOURCE\s*(\d+)", block, re.I)
        if match:
            sid = int(match.group(1))
            indexed[sid] = block
            if query_tokens:
                block_tokens = tokens(block)
                source_relevance[sid] = round(len(query_tokens & block_tokens) / max(1, len(query_tokens)), 3)

    relevant_sources = [score for score in source_relevance.values() if score > 0]
    average_source_relevance = round(sum(relevant_sources) / len(relevant_sources), 3) if relevant_sources else 0.0

    def split_atomic(claim: str) -> list[str]:
        """Split factual clauses while keeping enough subject context to verify them."""
        citation = " ".join(re.findall(r"\[S\d+\]", claim))
        body = re.sub(r"\[S\d+\]", "", claim).strip()
        parts = re.split(
            r"\s+(?:y|e|pero|aunque|sin embargo|and|but|however)\s+|\s*;\s*|\s*,\s+(?=(?:y|e|pero|aunque|and|but|however)\b)",
            body,
            flags=re.I,
        )
        parts = [re.sub(r"\s+", " ", p).strip(" -•") for p in parts if len(p.strip()) >= 18]
        if len(parts) <= 1:
            return [claim]
        # Carry the sentence's leading subject into short coordinate clauses.
        # Preserve the sentence subject for coordinate clauses, but do not
        # carry the first clause's numeric values into the second claim.
        subject_context = re.sub(
            r"\b(?:es|son|fue|era|será|está|están|is|are|was|were|will be|has|have)\b.*$",
            "",
            parts[0],
            flags=re.I,
        ).strip(" ,:;-")
        if not subject_context:
            subject_context = " ".join(parts[0].split()[:3])
        enriched = [f"{parts[0]} {citation}".strip()]
        for part in parts[1:]:
            contextual = f"{subject_context}: {part}" if subject_context else part
            enriched.append(f"{contextual} {citation}".strip())
        return enriched

    supported = 0
    unsupported = 0
    partial = 0
    uncited = 0
    issues: list[dict[str, Any]] = []
    claim_details: list[dict[str, Any]] = []

    for sentence in claims[:30]:
        atomic_claims = split_atomic(sentence)
        sentence_supported = 0
        sentence_unsupported = 0
        for claim in atomic_claims:
            citation_ids = [int(x) for x in re.findall(r"\[S(\d+)\]", claim)]
            clean_claim = re.sub(r"\[S\d+\]", " ", claim)
            claim_tokens = tokens(clean_claim)
            numbers = set(re.findall(r"(?<![\w])(?:20\d{2}|\d+(?:[.,]\d+)?%?)(?![\w])", clean_claim))
            candidates = [(sid, indexed[sid]) for sid in citation_ids if sid in indexed] if citation_ids else list(indexed.items())

            if citation_ids and not candidates:
                status = "unsupported"
                sentence_unsupported += 1
                unsupported += 1
                issues.append({"claim": claim[:260], "reason": "invalid_source_citation"})
                claim_details.append({
                    "claim": claim[:500], "status": status, "sources": citation_ids,
                    "support_score": 0.0, "unsupported_parts": ["invalid source citation"],
                })
                continue

            if not citation_ids:
                uncited += 1

            best_score = -1.0
            best_overlap = 0.0
            best_numbers = False
            best_sid = None
            for sid, block in candidates:
                block_tokens = tokens(block)
                overlap = len(claim_tokens & block_tokens) / max(1, len(claim_tokens))
                block_numbers = set(re.findall(r"(?<![\w])(?:20\d{2}|\d+(?:[.,]\d+)?%?)(?![\w])", block))
                number_ok = not numbers or numbers.issubset(block_numbers)
                score = overlap + (0.20 if number_ok else -0.20)
                if score > best_score:
                    best_score, best_overlap, best_sid, best_numbers = score, overlap, sid, number_ok

            support_score = max(0.0, min(1.0, best_overlap + (0.20 if best_numbers else 0.0)))
            if best_overlap >= 0.48 and best_numbers:
                status = "supported"
                sentence_supported += 1
                supported += 1
            elif best_overlap >= 0.32 and not numbers:
                status = "partial"
                sentence_supported += 1
                partial += 1
                issues.append({"claim": claim[:260], "reason": "partial_evidence_support", "source": best_sid})
            else:
                status = "unsupported"
                sentence_unsupported += 1
                unsupported += 1
                issues.append({"claim": claim[:260], "reason": "insufficient_evidence_support", "source": best_sid})

            claim_details.append({
                "claim": claim[:500],
                "status": status,
                "sources": citation_ids or ([best_sid] if best_sid is not None else []),
                "support_score": round(support_score, 3),
                "unsupported_parts": [] if status == "supported" else [claim[:240]],
            })

        # A sentence containing both supported and unsupported atomic claims is partial.
        if sentence_supported and sentence_unsupported:
            sentence_detail = {"claim": sentence[:500], "status": "partial", "sources": [], "support_score": 0.0}
            claim_details.append(sentence_detail)

    total = len(claim_details)
    return {
        # Partial support is not equivalent to verification. A response may still be
        # useful, but the caller must not label it fully verified when any factual
        # claim is only partially grounded in the retrieved evidence.
        "valid": unsupported == 0 and partial == 0,
        "claim_count": total,
        "supported_count": supported,
        "unsupported_count": unsupported,
        "partial_count": partial,
        "uncited_count": uncited,
        "issues": issues[:8],
        "claim_details": claim_details[:40],
        "reason": "claims_checked",
        "skipped_claims": skipped,
        "source_relevance": source_relevance,
        "average_source_relevance": average_source_relevance,
        "relevant_source_count": sum(1 for score in source_relevance.values() if score >= 0.12),
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

        verification_profile = context.get("verification_profile") or (context.get("bitey_brain") or {}).get("verification_profile") or ["fact"]
        calculation_mode = "calculation" in verification_profile
        inference_mode = "inference" in verification_profile
        opinion_mode = "opinion" in verification_profile

        evidence_required = bool(context.get("evidence_required"))
        if calculation_mode and not evidence:
            evidence_alignment = 1.0
        if opinion_mode and not evidence:
            evidence_alignment = max(evidence_alignment, 0.90)
        if evidence_required and not evidence:
            evidence_alignment = 0.35
            reasons.append("evidence_required_but_unavailable")
            if not self._UNCERTAINTY.search(text):
                contradiction_risk += 0.25
                reasons.append("missing_evidence_disclosure")
        elif evidence:
            # Evidence quality now affects the gate. A high-authority source can
            # carry more weight than a larger pile of weak or duplicate pages.
            source_quality = float(context.get("evidence_quality", 0.0) or 0.0)
            independent_sources = int(context.get("independent_source_count", 0) or 0)
            strong_sources = int(context.get("strong_source_count", 0) or 0)
            if source_quality:
                evidence_alignment = min(0.95, 0.55 + source_quality * 0.40)
                if independent_sources >= 2:
                    evidence_alignment = min(1.0, evidence_alignment + 0.08)
                if strong_sources >= 2:
                    evidence_alignment = min(1.0, evidence_alignment + 0.05)
            else:
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

        answer_verification = context.get("answer_verification") or {}
        if inference_mode and evidence:
            # Inferences may be valid without verbatim source wording, but must not
            # be scored as unsupported facts solely because the inference is novel.
            if int(answer_verification.get("unsupported_count", 0) or 0) > 0:
                reasons.append("inference_requires_explicit_basis")
        unsupported_count = int(answer_verification.get("unsupported_count", 0) or 0)
        partial_count = int(answer_verification.get("partial_count", 0) or 0)
        if evidence and unsupported_count > 0 and not (inference_mode and not evidence_required):
            evidence_alignment = min(evidence_alignment, 0.45)
            reasons.append("unsupported_answer_claims")
        elif evidence and partial_count > 0 and evidence_required:
            # Partial grounding is not enough for a research answer to pass as
            # fully verified. Keep the answer usable, but force a revision.
            evidence_alignment = min(evidence_alignment, 0.45)
            reasons.append("partial_answer_claims")

        quality = max(0.0, min(1.0, quality))
        safety = max(0.0, min(1.0, safety))
        contradiction_risk = max(0.0, min(1.0, contradiction_risk))
        confidence = max(0.0, min(1.0, quality * 0.4 + evidence_alignment * 0.25 + safety * 0.25 + (1.0 - contradiction_risk) * 0.10))

        if safety < 0.60:
            decision = "reject"
        elif evidence_required and (unsupported_count > 0 or partial_count > 0):
            decision = "revise"
        elif evidence_required and evidence_alignment < 0.50:
            decision = "revise"
        elif confidence < 0.60:
            decision = "revise"
        else:
            decision = "accept"

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
