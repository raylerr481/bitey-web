"""General-purpose Bitey cognitive pipeline.

This module generalizes proven patterns from the BiteFixes backend without
importing or modifying BiteFixes. Domain knowledge is supplied as context;
the cognitive pipeline itself remains domain-neutral.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re


@dataclass
class CognitiveState:
    perception: dict[str, Any] = field(default_factory=dict)
    intention: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    decision: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "perception": self.perception,
            "intention": self.intention,
            "context": self.context,
            "plan": self.plan,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "decision": self.decision,
        }


class CognitiveModel:
    """Domain-neutral cognition built from reusable enterprise-AI patterns."""

    _DOMAIN_HINTS = {
        "trading": ("trading", "trade", "forex", "stock", "mercado", "tradingview", "mt5"),
        "support": ("ticket", "soporte", "error", "incidencia", "cliente", "reparación", "repair"),
        "programming": ("código", "codigo", "python", "javascript", "api", "bug", "programar"),
        "marketing": ("marketing", "ventas", "campaña", "cliente", "publicidad", "seo"),
        "research": ("investiga", "investigar", "research", "evidencia", "fuentes", "estudio"),
    }

    def perceive(self, message: str) -> dict[str, Any]:
        text = message.strip()
        return {
            "message_length": len(text),
            "language_hint": self._language_hint(text),
            "question": "?" in text or bool(re.match(r"^(que|qué|como|cómo|por que|por qué|what|how|why)\b", text.lower())),
        }

    def infer_intention(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        text = message.lower()
        scores = {domain: sum(1 for hint in hints if hint in text) for domain, hints in self._DOMAIN_HINTS.items()}
        domain = max(scores, key=scores.get) if scores and max(scores.values()) else "general"
        return {"domain": domain, "scores": scores, "source": "generalized_context_inference"}

    def build_plan(self, message: str, context: dict[str, Any], intention: dict[str, Any]) -> dict[str, Any]:
        needs_evidence = bool(context.get("research")) or intention.get("domain") == "research"
        return {
            "objective": "answer_or_assist",
            "domain": intention.get("domain", "general"),
            "needs_evidence": needs_evidence,
            "requires_specialized_module": intention.get("domain") not in {"general", "research"},
        }

    def evaluate(self, state: CognitiveState, *, evidence_available: bool = False) -> CognitiveState:
        base = 0.55
        if state.intention.get("domain") != "general": base += 0.10
        if state.plan.get("needs_evidence"):
            base += 0.15 if evidence_available else -0.10
        if state.context.get("enterprise") is not None: base += 0.05
        state.evidence = {"available": evidence_available}
        state.confidence = max(0.0, min(1.0, base))
        state.decision = {
            "mode": "respond",
            "domain": state.intention.get("domain", "general"),
            "confidence": state.confidence,
            "evidence_required": state.plan.get("needs_evidence", False),
        }
        return state

    def process(self, message: str, context: dict[str, Any] | None = None, *, evidence_available: bool = False) -> CognitiveState:
        ctx = context or {}
        perception = self.perceive(message)
        intention = self.infer_intention(message, ctx)
        plan = self.build_plan(message, ctx, intention)
        state = CognitiveState(perception=perception, intention=intention, context=ctx, plan=plan)
        return self.evaluate(state, evidence_available=evidence_available)

    @staticmethod
    def _language_hint(text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in (" que ", "cómo", "quiero", "para", "puede")): return "es"
        if any(token in lowered for token in (" que ", "como", "quero", "para", "pode")): return "pt"
        if any(token in lowered for token in (" what ", "how ", "want ", "can ", "please")): return "en"
        return "unknown"
