from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re
from difflib import SequenceMatcher


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
        # Keep domain hints semantically specific. Generic words such as
        # "tiempo", "mercado" and "cliente" are intentionally excluded here;
        # they need contextual evidence before selecting a specialized domain.
        "weather": ("temperatura", "clima", "weather", "temperature", "forecast", "previsão", "previsao"),
        "finance": ("precio", "precios", "cotización", "cotizacion", "acción", "acciones", "stock", "dividendo", "dividendos", "finanzas"),
        "trading": ("trading", "trade", "forex", "stock", "tradingview", "mt5"),
        "support": ("ticket", "soporte", "error", "incidencia", "reparación", "repair"),
        "programming": ("código", "codigo", "python", "javascript", "api", "bug", "programar"),
        "marketing": ("marketing", "ventas", "campaña", "publicidad", "seo"),
        "research": ("investiga", "investigar", "research", "evidencia", "fuentes", "estudio"),
    }

    _STRONG_INTENT = {
        "research": ("investiga", "investigar", "research", "compara", "fuentes", "evidencia"),
        "trading": ("eurusd", "gbpusd", "xauusd", "btc/usd", "btcusd", "forex", "mt5", "tradingview", "estrategia de trading", "bot de trading", "bot para trading", "señal de trading", "analiza btc", "analiza eth", "analiza eurusd", "backtest", "backtesting"),
        "weather": ("qué temperatura", "que temperatura", "temperatura actual", "clima actual", "pronóstico", "pronostico", "weather", "tiempo hoy", "el tiempo hoy", "tiempo en", "clima en", "como esta el tiempo", "cómo está el tiempo", "com esta el tiempo", "com esta el clima"),
        "programming": ("escribe código", "escribe codigo", "programa", "implementa", "debug", "api rest", "crear un bot", "crea un bot", "puedes crear bot"),
        "finance": ("precio de", "precio ahora", "cotiza", "cotización", "cotizacion", "acciones de", "acción de", "dividendos", "valor de mercado"),
    }

    _GREETING_PATTERNS = (
        r"^hola[!,.¡¿?\s]*$", r"^holi[!,.¡¿?\s]*$", r"^hello[!,.¡¿?\s]*$",
        r"^hi[!,.¡¿?\s]*$", r"^hey[!,.¡¿?\s]*$", r"^buenos?\s+d[ií]as[!,.¡¿?\s]*$",
        r"^buenas\s+(tardes|noches)[!,.¡¿?\s]*$", r"^boa\s+(tarde|noite)[!,.¡¿?\s]*$",
    )

    _IDENTITY_PATTERNS = (
        r"^(?:[¿?\s]*)qu[ií]e?n\s+eres[?!.,¡¿\s]*$",
        r"^(?:[¿?\s]*)qu[eé]\s+eres[?!.,¡¿\s]*$",
        r"^(?:[¿?\s]*)qu[eé]\s+puedes\s+hacer[?!.,¡¿\s]*$",
        r"^(?:[¿?\s]*)qu[eé]\s+haces[?!.,¡¿\s]*$",
        r"^(?:[¿?\s]*)c[oó]mo\s+funcionas[?!.,¡¿\s]*$",
        r"^(?:[¿?\s]*)what\s+are\s+you[?!.,\s]*$",
        r"^(?:[¿?\s]*)who\s+are\s+you[?!.,\s]*$",
        r"^(?:[¿?\s]*)what\s+can\s+you\s+do[?!.,\s]*$",
        r"^(?:[¿?\s]*)qual\s+[eé]\s+voc[eê][?!.,\s]*$",
        r"^(?:[¿?\s]*)o\s+que\s+voc[eê]\s+faz[?!.,\s]*$",
    )

    _CONCEPTUAL_CUES = (
        "qué es", "que es", "qué son", "que son", "qué significa", "que significa",
        "cómo funciona", "como funciona", "definición", "definicion", "define",
        "explica", "explícame", "explicame", "concepto", "what is", "what are",
        "how does", "qual é", "o que é", "o que são", "como funciona",
    )

    _FOLLOWUP_WORDS = ("eso", "esto", "ello", "ese", "esa", "seguir", "continúa", "continua", "analízalo", "analizalo", "hazlo", "explícalo", "explicalo")
    _MARKET_INSTRUMENT_RE = re.compile(r"\b(?:[A-Z]{2,12}(?:USDT|USD)|[A-Z]{6}|XAUUSD|XAGUSD)\b", re.I)
    _MARKET_ACTION_CUES = ("precio", "cotización", "cotizacion", "valor", "cuánto vale", "cuanto vale", "cómo está", "como esta", "ahora", "ahora mismo", "cotiza")


    _ROUTING_ALIASES = {
        "hoka": "hola", "holaa": "hola", "holla": "hola", "ola": "hola", "olaa": "hola",
        "tienpo": "tiempo", "timepo": "tiempo", "tiemp": "tiempo", "cllima": "clima", "climma": "clima", "com": "como",
        "contiua": "continua", "contina": "continua", "continuaaa": "continua",
        "preico": "precio", "prceio": "precio", "cotizacon": "cotizacion", "accin": "accion",
    }

    @classmethod
    def _routing_vocabulary(cls) -> tuple[str, ...]:
        groups = list(cls._DOMAIN_HINTS.values()) + list(cls._STRONG_INTENT.values()) + [cls._FOLLOWUP_WORDS]
        words = {"hola", "holi", "hello", "hey", "buenas", "temperatura", "tiempo", "clima", "continua", "continúa"}
        for group in groups:
            for word in group:
                if len(word) >= 4 and " " not in word:
                    words.add(word.lower())
        return tuple(words)

    @classmethod
    def _normalize_for_routing(cls, text: str) -> str:
        """Correct only high-confidence typos for intent routing."""
        vocabulary = cls._routing_vocabulary()
        tokens = re.findall(r"[\wÀ-ÿ]+|[^\wÀ-ÿ]+", text.strip(), re.UNICODE)
        normalized = []
        for token in tokens:
            if not re.fullmatch(r"[\wÀ-ÿ]+", token, re.UNICODE):
                normalized.append(token)
                continue
            lowered = token.lower()
            if lowered in cls._ROUTING_ALIASES:
                normalized.append(cls._ROUTING_ALIASES[lowered])
                continue
            if len(lowered) >= 4:
                best = max(vocabulary, key=lambda candidate: SequenceMatcher(None, lowered, candidate).ratio())
                ratio = SequenceMatcher(None, lowered, best).ratio()
                if ratio >= 0.88 and abs(len(lowered) - len(best)) <= 2:
                    normalized.append(best)
                    continue
            normalized.append(token)
        return "".join(normalized)

    @classmethod
    def _is_greeting(cls, text: str) -> bool:
        normalized = " ".join(text.lower().strip().split())
        return any(re.fullmatch(pattern, normalized, flags=re.I) for pattern in cls._GREETING_PATTERNS)

    @classmethod
    def _is_identity_request(cls, text: str) -> bool:
        normalized = " ".join(text.lower().strip().split())
        return any(re.fullmatch(pattern, normalized, flags=re.I) for pattern in cls._IDENTITY_PATTERNS)

    def perceive(self, message: str) -> dict[str, Any]:
        text = self._normalize_for_routing(message)
        words = len(text.split())
        return {
            "message_length": len(text),
            "word_count": words,
            "language_hint": self._language_hint(text),
            "question": "?" in text or bool(re.match(r"^(que|qué|como|cómo|por que|por qué|what|how|why|qual|onde|quando)\b", text.lower())),
            "has_url": bool(re.search(r"https?://|www\.", text, re.I)),
            "greeting": self._is_greeting(text),
            "identity_request": self._is_identity_request(text),
            "complexity_signal": min(1.0, 0.20 + min(0.30, words / 180)),
        }

    def infer_intention(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        text = self._normalize_for_routing(message).lower()
        scores = {domain: sum(1 for hint in hints if hint in text) for domain, hints in self._DOMAIN_HINTS.items()}
        # Current-data questions can be written with imperfect spelling. Treat
        # a normalized weather cue plus a temporal cue as a semantic weather
        # intent even when the sentence is not grammatically complete.
        weather_temporal = any(x in text for x in ("tiempo", "clima", "temperatura", "weather")) and any(x in text for x in ("hoy", "ahora", "actual", "actualmente", "ahora mismo"))
        if weather_temporal:
            scores["weather"] = max(scores.get("weather", 0), 2)
        # Current financial facts need fresh evidence rather than static knowledge.
        finance_current = any(x in text for x in ("precio", "cotización", "cotizacion", "cotiza", "acciones", "dividendos")) and any(x in text for x in ("ahora", "hoy", "actual", "actualmente", "último", "última", "cuánto", "cuanto", "vale"))
        if finance_current:
            scores["finance"] = max(scores.get("finance", 0), 2)
        conceptual = any(cue in text for cue in self._CONCEPTUAL_CUES)
        greeting = self._is_greeting(text)
        identity_request = self._is_identity_request(text)
        strong_scores = {domain: sum(1 for hint in hints if hint in text) for domain, hints in self._STRONG_INTENT.items()}
        # Explicit market instruments plus a market-action question are a
        # strong trading signal; the instrument alone is not. This keeps
        # conceptual questions such as "qué es Bitcoin" in the general brain.
        market_instrument = bool(self._MARKET_INSTRUMENT_RE.search(message))
        market_action = any(cue in text for cue in self._MARKET_ACTION_CUES)
        if market_instrument and market_action:
            strong_scores["trading"] = strong_scores.get("trading", 0) + 2

        if greeting:
            return {
                "domain": "general",
                "intent": "greeting",
                "scores": {**scores, "general": 1},
                "confidence": 0.98,
                "source": "structured_greeting_intent",
                "response_guidance": "acknowledge_the_user_greeting_naturally_and_continue_the_conversation",
            }

        # Questions about Bitey's own identity/capabilities are conversational
        # and do not require external evidence or a specialized module.
        if identity_request:
            return {
                "domain": "general",
                "intent": "self_identity",
                "scores": {**scores, "general": 2},
                "confidence": 0.98,
                "source": "structured_self_identity_intent",
                "response_guidance": "describe_bitey_identity_capabilities_and_scope_without_external_research",
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
        if intent in {"greeting", "self_identity"}:
            return {
                "objective": "acknowledge_greeting_and_continue_conversation" if intent == "greeting" else "answer_bitey_identity_and_capabilities",
                "domain": "general",
                "intent": intent,
                "needs_evidence": False,
                "freshness_required": False,
                "requires_specialized_module": False,
                "verification_required": False,
                "stop_condition": "natural_conversational_response",
            }
        freshness = domain in {"weather", "finance"} or bool(context.get("freshness_required"))
        evidence = freshness or bool(context.get("research") or context.get("requires_web_research") or context.get("needs_web")) or domain == "research"
        # Detect compound requests so the planner can preserve the user's requested sequence.
        lower_message = message.lower()
        step_cues = (" y luego ", " después ", " despues ", " luego ", " después de ", " despues de ", "then ", "after that", "and then", "primero", "first")
        compound = any(cue in lower_message for cue in step_cues)
        action_cues = ("analiza", "analizar", "busca", "buscar", "investiga", "calcula", "calcular", "compara", "explica", "resume", "responde", "verifica", "revisa", "implementa")
        action_count = sum(1 for cue in action_cues if cue in lower_message)
        multi_step = compound or action_count >= 2
        steps = []
        if multi_step:
            if any(cue in lower_message for cue in ("busca", "buscar", "investiga", "investigar", "fuentes")): steps.append("retrieve_evidence")
            if any(cue in lower_message for cue in ("calcula", "calcular", "porcentaje", "cuánto", "cuanto")): steps.append("calculate")
            if any(cue in lower_message for cue in ("analiza", "analizar", "revisa", "revisar", "compara")): steps.append("analyze")
            if any(cue in lower_message for cue in ("verifica", "verificar", "contrasta", "contrastar")): steps.append("verify")
            steps.append("synthesize_answer")
        return {
            "objective": "retrieve_current_data_and_answer" if freshness else "answer_or_assist",
            "domain": domain,
            "needs_evidence": evidence,
            "freshness_required": freshness,
            "requires_specialized_module": domain not in {"general", "research", "weather"},
            "verification_required": evidence or domain == "research" or multi_step,
            "multi_step": multi_step,
            "steps": list(dict.fromkeys(steps)),
            "stop_condition": "all_planned_steps_completed_and_verified" if multi_step else ("fresh_source_retrieved_and_validated" if freshness else "sufficient_confidence"),
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
