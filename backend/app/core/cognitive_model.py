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

    _STRONG_INTENT = {
        "research": ("investiga", "investigar", "research", "compara", "fuentes", "evidencia"),
        "trading": ("eurusd", "gbpusd", "xauusd", "btc/usd", "btcusd", "forex", "acciones", "mercado", "mt5", "tradingview", "estrategia de trading", "bot de trading", "bot para trading", "señal de trading", "analiza btc", "analiza eth", "analiza eurusd", "backtest", "backtesting"),
        "weather": ("qué temperatura", "que temperatura", "temperatura actual", "clima actual", "pronóstico", "pronostico", "weather"),
        "programming": ("escribe código", "escribe codigo", "programa", "implementa", "debug", "api rest", "crear un bot", "crea un bot", "puedes crear bot"),
    }

    _GREETING_PATTERNS = (
        r"^hola[!,.¡¿?\s]*$", r"^holi[!,.¡¿?\s]*$", r"^hello[!,.¡¿?\s]*$",
        r"^hi[!,.¡¿?\s]*$", r"^hey[!,.¡¿?\s]*$", r"^buenos?\s+d[ií]as[!,.¡¿?\s]*$",
        r"^buenas\s+(tardes|noches)[!,.¡¿?\s]*$", r"^boa\s+(tarde|noite)[!,.¡¿?\s]*$",
    )

    _CONCEPTUAL_CUES = (
        "qué es", "que es", "qué son", "que son", "qué significa", "que significa",
        "cómo funciona", "como funciona", "definición", "definicion", "define",
        "explica", "explícame", "explicame", "concepto", "what is", "what are",
        "how does", "qual é", "o que é", "o que são", "como funciona",
    )

    _FOLLOWUP_WORDS = ("eso", "esto", "ello", "ese", "esa", "seguir", "continúa", "continua", "analízalo", "analizalo", "hazlo", "explícalo", "explicalo")

    @classmethod
    def _is_greeting(cls, text: str) -> bool:
        normalized = " ".join(text.lower().strip().split())
        return any(re.fullmatch(pattern, normalized, flags=re.I) for pattern in cls._GREETING_PATTERNS)

    def perceive(self, message: str) -> dict[str, Any]:
        text = message.strip()
        words = len(text.split())
        return {
            "message_length": len(text),
            "word_count": words,
            "language_hint": self._language_hint(text),
            "question": "?" in text or bool(re.match(r"^(que|qué|como|cómo|por que|por qué|what|how|why|qual|onde|quando)\b", text.lower())),
            "has_url": bool(re.search(r"https?://|www\.", text, re.I)),
            "greeting": self._is_greeting(text),
            "complexity_signal": min(1.0, 0.20 + min(0.30, words / 180)),
        }

    def infer_intention(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        text = message.lower().strip()
        scores = {domain: sum(1 for hint in hints if hint in text) for domain, hints in self._DOMAIN_HINTS.items()}
        conceptual = any(cue in text for cue in self._CONCEPTUAL_CUES)
        greeting = self._is_greeting(text)
        strong_scores = {domain: sum(1 for hint in hints if hint in text) for domain, hints in self._STRONG_INTENT.items()}

        # A standalone greeting is always conversational/general. It must not
        # activate a specialized module or inherit a stale domain from the session.
        if greeting:
            return {
                "domain": "general",
                "intent": "greeting",
                "scores": {**scores, "general": 1},
                "confidence": 0.98,
                "source": "structured_greeting_intent",
                "response_guidance": "acknowledge_the_user_greeting_naturally_and_continue_the_conversation",
            }

        if conceptual:
            for domain in strong_scores:
                if domain != "weather" or not any(x in text for x in ("actual", "ahora", "hoy", "pronóstico", "pronostico")):
                    strong_scores[domain] = 0
            scores["general"] = 1

        max_strong = max(strong_scores.values(), default=0)
        if max_strong:
            strong_domains = [d for d, score in strong_scores.items() if score == max_strong]
            if len(strong_domains) == 1:
                scores[strong_domains[0]] += 2

        explicit_domain = str(context.get("domain") or "").strip().lower()
        current_signal = max(scores.values(), default=0)
        is_followup = any(token in text for token in self._FOLLOWUP_WORDS)
        if explicit_domain in scores and current_signal == 0 and is_followup:
            scores[explicit_domain] += 1

        order = ["general"] + list(self._DOMAIN_HINTS)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], order.index(item[0]) if item[0] in order else len(order)))
        top_domain, top_score = ranked[0] if ranked else ("general", 0)
        second_score = ranked[1][1] if len(ranked) > 1 else 0
        if top_score == 0:
            top_domain = "general"
        confidence = 0.55 if top_score else 0.35
        if top_score > second_score:
            confidence += min(0.25, (top_score - second_score) * 0.08)
        return {"domain": top_domain, "intent": "answer_or_assist", "scores": scores, "confidence": min(1.0, confidence), "source": "structured_intent_inference"}

    def build_plan(self, message: str, context: dict[str, Any], intention: dict[str, Any]) -> dict[str, Any]:
        domain = intention.get("domain", "general")
        intent = intention.get("intent", "answer_or_assist")
        if intent == "greeting":
            return {
                "objective": "acknowledge_greeting_and_continue_conversation",
                "domain": "general",
                "intent": "greeting",
                "needs_evidence": False,
                "freshness_required": False,
                "requires_specialized_module": False,
                "verification_required": False,
                "stop_condition": "natural_conversational_greeting_response",
            }
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
            "intent": state.intention.get("intent", "answer_or_assist"),
            "confidence": state.confidence,
            "evidence_required": bool(state.plan.get("needs_evidence")),
            "freshness_required": bool(state.plan.get("freshness_required")),
        }
        return state

    def process(self, message: str, context: dict[str, Any] | None = None, *, evidence_available: bool = False) -> CognitiveState:
        ctx = context or {}
        cached = ctx.get("_cognitive_state")
        if isinstance(cached, CognitiveState):
            cached_message = str(cached.context.get("_cognitive_message") or "").strip()
            cached_available = bool(cached.evidence.get("available", False))
            if cached_message == message.strip():
                if cached_available != bool(evidence_available):
                    return self.evaluate(cached, evidence_available=evidence_available)
                return cached
        perception = self.perceive(message)
        intention = self.infer_intention(message, ctx)
        plan = self.build_plan(message, ctx, intention)
        state = CognitiveState(perception=perception, intention=intention, context=ctx, plan=plan)
        state.context["_cognitive_message"] = message.strip()
        return self.evaluate(state, evidence_available=evidence_available)

    @staticmethod
    def _language_hint(text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ("cómo", "qué", "quiero", "puede", "tiempo", "clima")): return "es"
        if any(token in lowered for token in ("como", "quero", "pode", "previsao", "clima")): return "pt"
        if any(token in lowered for token in ("what ", "how ", "want ", "can ", "please", "weather")): return "en"
        return "unknown"
