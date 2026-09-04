"""General-purpose Bitey cognitive state and intent model.

This layer creates structured task state. It is not the language-generation
model and does not select a provider. The executive Brain consumes its state.
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
        return {"perception": self.perception, "intention": self.intention, "context": self.context, "plan": self.plan, "evidence": self.evidence, "confidence": self.confidence, "decision": self.decision}


class CognitiveModel:
    """Domain-neutral structured cognition used before model routing."""

    _DOMAIN_HINTS = {
        "weather": ("temperatura", "clima", "tiempo", "weather", "temperature", "forecast", "previsão", "previsao"),
        "trading": ("trading", "trade", "forex", "stock", "mercado", "tradingview", "mt5"),
        "support": ("ticket", "soporte", "error", "incidencia", "cliente", "reparación", "repair"),
        "programming": ("código", "codigo", "python", "javascript", "api", "bug", "programar"),
        "marketing": ("marketing", "ventas", "campaña", "cliente", "publicidad", "seo"),
        "research": ("investiga", "investigar", "research", "evidencia", "fuentes", "estudio"),
    }

    # High-signal expressions disambiguate common lexical ties. They are
    # intent features, not provider/model selection rules.
    _STRONG_INTENT = {
        "research": ("investiga", "investigar", "research", "compara", "fuentes", "evidencia"),
        "trading": ("eurusd", "gbpusd", "xauusd", "bitcoin", "btc", "forex", "acciones", "compra eurusd", "vende eurusd"),
        "weather": ("qué temperatura", "que temperatura", "temperatura actual", "clima actual", "pronóstico", "pronostico", "weather"),
        "programming": ("escribe código", "escribe codigo", "programa", "implementa", "debug", "api rest"),
    }

    def perceive(self, message: str) -> dict[str, Any]:
        text = message.strip()
        words = len(text.split())
        return {
            "message_length": len(text),
            "word_count": words,
            "language_hint": self._language_hint(text),
            "question": "?" in text or bool(re.match(r"^(que|qué|como|cómo|por que|por qué|what|how|why|qual|como|onde|quando)\b", text.lower())),
            "has_url": bool(re.search(r"https?://|www\.", text, re.I)),
            "complexity_signal": min(1.0, 0.20 + min(0.30, words / 180)),
        }

    def infer_intention(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        text = message.lower()
        scores = {domain: sum(1 for hint in hints if hint in text) for domain, hints in self._DOMAIN_HINTS.items()}
        strong_scores = {domain: sum(1 for hint in hints if hint in text) for domain, hints in self._STRONG_INTENT.items()}
        max_strong = max(strong_scores.values(), default=0)
        if max_strong:
            strong_domains = [d for d, score in strong_scores.items() if score == max_strong]
            if len(strong_domains) == 1:
                scores[strong_domains[0]] += 2

        # Prefer explicit domain context when supplied by an upstream caller.
        explicit_domain = str(context.get("domain") or "").strip().lower()
        if explicit_domain in scores:
            scores[explicit_domain] += 2

        order = list(self._DOMAIN_HINTS)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], order.index(item[0])))
        top_domain, top_score = ranked[0] if ranked else ("general", 0)
        second_score = ranked[1][1] if len(ranked) > 1 else 0
        if top_score == 0:
            top_domain = "general"
        confidence = 0.55 if top_score else 0.35
        if top_score > second_score:
            confidence += min(0.25, (top_score - second_score) * 0.08)
        return {"domain": top_domain, "scores": scores, "confidence": min(1.0, confidence), "source": "structured_intent_inference"}

    def build_plan(self, message: str, context: dict[str, Any], intention: dict[str, Any]) -> dict[str, Any]:
        domain = intention.get("domain", "general")
        freshness = domain == "weather" or bool(context.get("freshness_required"))
        evidence = freshness or bool(context.get("research") or context.get("requires_web_research") or context.get("needs_web")) or domain == "research"
        return {
            "objective": "retrieve_current_data_and_answer" if freshness else "answer_or_assist",
            "domain": domain,
            "needs_evidence": evidence,
            "freshness_required": freshness,
            "requires_specialized_module": domain not in {"general", "research", "weather"},
            "verification_required": evidence or domain == "research",
            "stop_condition": "fresh_source_retrieved_and_validated" if freshness else "sufficient_confidence",
        }

    def evaluate(self, state: CognitiveState, *, evidence_available: bool = False) -> CognitiveState:
        base = float(state.intention.get("confidence", 0.35))
        if state.plan.get("needs_evidence"):
            base += 0.15 if evidence_available else -0.05
        state.evidence = {"available": evidence_available}
        state.confidence = max(0.0, min(1.0, base))
        state.decision = {
            "mode": "retrieve_then_respond" if state.plan.get("needs_evidence") else "respond",
            "domain": state.intention.get("domain", "general"),
            "confidence": state.confidence,
            "evidence_required": bool(state.plan.get("needs_evidence")),
            "freshness_required": bool(state.plan.get("freshness_required")),
        }
        return state

    def process(self, message: str, context: dict[str, Any] | None = None, *, evidence_available: bool = False) -> CognitiveState:
        ctx = context or {}
        cached = ctx.get("_cognitive_state")
        if isinstance(cached, CognitiveState):
            cached_available = bool(cached.evidence.get("available", False))
            if cached_available != bool(evidence_available):
                return self.evaluate(cached, evidence_available=evidence_available)
            return cached
        perception = self.perceive(message)
        intention = self.infer_intention(message, ctx)
        plan = self.build_plan(message, ctx, intention)
        state = CognitiveState(perception=perception, intention=intention, context=ctx, plan=plan)
        return self.evaluate(state, evidence_available=evidence_available)

    @staticmethod
    def _language_hint(text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ("cómo", "qué", "quiero", "puede", "tiempo", "clima")): return "es"
        if any(token in lowered for token in ("como", "quero", "pode", "previsao", "clima")): return "pt"
        if any(token in lowered for token in ("what ", "how ", "want ", "can ", "please", "weather")): return "en"
        return "unknown"
