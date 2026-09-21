from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import hashlib
import re
from difflib import SequenceMatcher


@dataclass
class CognitiveFrame:
    """Portable, provider-independent representation of a cognitive turn."""

    input_text: str
    language: str = "unknown"
    domain: str = "general"
    intent: str = "answer_or_assist"
    entities: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    evidence_required: bool = False
    evidence_available: bool = False
    confidence: float = 0.0
    plan: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)

    @property
    def signature(self) -> str:
        raw = "|".join((self.language, self.domain, self.intent, self.input_text.lower().strip()))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_text": self.input_text,
            "language": self.language,
            "domain": self.domain,
            "intent": self.intent,
            "entities": self.entities,
            "constraints": self.constraints,
            "evidence_required": self.evidence_required,
            "evidence_available": self.evidence_available,
            "confidence": self.confidence,
            "plan": self.plan,
            "risk_flags": self.risk_flags,
            "signature": self.signature,
        }


class BiteyCognitiveArchitecture:
    """Independent cognition layer used by every Bitey model/provider.

    It is deliberately model-agnostic: external LLMs provide language
    generation when available, while this layer owns perception, intent,
    planning, safety boundaries and decision structure.
    """

    DOMAIN_HINTS = {
        "weather": ("temperatura", "clima", "tiempo", "weather", "temperature", "forecast", "pronóstico", "pronostico", "previsão", "previsao"),
        # Generic concepts such as "mercado", "bolsa" and "bot" are not\n        # sufficient to enter SBT. Trading requires an explicit market\n        # operation, instrument, timeframe, or technical-market context.\n        "trading": ("trading", "trade", "forex", "stock", "mt5", "tradingview"),
        "support": ("ticket", "soporte", "error", "incidencia", "reparación", "repair", "cctv"),
        "programming": ("código", "codigo", "python", "javascript", "api", "bug", "programar", "github"),
        "marketing": ("marketing", "ventas", "campaña", "publicidad", "seo"),
        "research": ("investiga", "investigar", "research", "evidencia", "fuentes", "estudio", "analiza"),
        "health": (
            "salud", "health", "enfermedad", "enfermedades", "disease", "síntoma", "síntomas", "sintoma", "sintomas",
            "symptom", "sida", "vih", "hiv", "tratamiento", "tratamientos", "treatment", "medicina", "medical",
            "médico", "médica", "diagnóstico", "diagnostico", "diagnosis", "infección", "infecciones", "infection",
            "cáncer", "cancer", "virus", "bacteria", "vacuna", "vacunación", "hospital", "medicación", "medicamento",
        ),
    }

    MARKET_INSTRUMENT_RE = re.compile(
        r"\b(?:[A-Z]{2,6}(?:USDT|USDC|USD|EUR|JPY|GBP|CHF|AUD|CAD|NZD)|BTC(?:USD|USDT|USDC)?|ETH(?:USD|USDT|USDC)?|XAUUSD|XAGUSD)\b",
        re.I,
    )
    MARKET_TIMEFRAME_RE = re.compile(r"\b(?:M1|M3|M5|M15|M30|H1|H2|H4|D1|W1|MN1)\b", re.I)
    MARKET_CONTEXT_RE = re.compile(
        r"\b(?:vela|velas|candela|candles|gráfico|grafico|chart|precio|cotización|cotizacion|spread|bid|ask|"
        r"soporte|resistencia|tendencia|trend|scalp|scalping|forex|crypto|cripto|futuros|futures|"
        r"indicador|rsi|macd|ema|sma|atr|liquidez|liquidity|fvg|order\s+block|smart\s+money)\b",
        re.I,
    )

    CONCEPTUAL_CUES = (\n        "qué es", "que es", "qué son", "que son", "qué significa", "que significa",\n        "definición", "definicion", "define", "concepto", "cómo funciona", "como funciona",\n        "what is", "what are", "how does", "qual é", "o que é", "o que são", "como funciona",\n    )\n\n    GREETING_ALIASES = {
        "hola", "holaa", "holla", "hoka", "hol", "ola", "olaa", "oi", "hey", "hello", "hi",
    }

    @classmethod
    def _normalize_for_routing(cls, text: str) -> str:
        """Normalize obvious conversational typos without rewriting user content."""
        message = text.strip()
        tokens = re.findall(r"[\wÀ-ÿ]+|[^\wÀ-ÿ]+", message, re.UNICODE)
        normalized = []
        for token in tokens:
            if not re.fullmatch(r"[\wÀ-ÿ]+", token, re.UNICODE):
                normalized.append(token)
                continue
            lowered = token.lower()
            if lowered in cls.GREETING_ALIASES:
                normalized.append("hola")
                continue
            if len(lowered) >= 3:
                best = max(cls.GREETING_ALIASES, key=lambda candidate: SequenceMatcher(None, lowered, candidate).ratio())
                if SequenceMatcher(None, lowered, best).ratio() >= 0.80:
                    normalized.append("hola")
                    continue
            normalized.append(token)
        return "".join(normalized)

    def perceive(self, text: str, context: dict[str, Any]) -> CognitiveFrame:
        original_message = text.strip()
        message = self._normalize_for_routing(original_message)
        language = self._language(message, context)
        domain, domain_score = self._domain(message)
        market_instrument = bool(self.MARKET_INSTRUMENT_RE.search(message))
        market_timeframe = bool(self.MARKET_TIMEFRAME_RE.search(message))
        market_context = bool(self.MARKET_CONTEXT_RE.search(message))
        market_signal = int(market_instrument) + int(market_timeframe) + int(market_context)

        # A market instrument plus a timeframe is an explicit trading request,
        # even when generic research words such as "analiza" are present.
        if market_instrument and market_timeframe:
            domain = "trading"
            domain_score = max(domain_score, 3)
        elif market_instrument and market_context:
            domain = "trading"
            domain_score = max(domain_score, 3)
        elif market_signal >= 2 and domain == "research":
            domain = "trading"
            domain_score = max(domain_score, 2)

        intent = self._intent(message, domain)
        evidence_required = bool(context.get("research")) or domain in {"weather", "research", "health", "trading"}
        risk_flags: list[str] = []
        lowered = message.lower()
        if domain == "trading" and any(token in lowered for token in ("comprar", "vender", "ejecuta", "orden", "live", "real")):
            risk_flags.append("financial_action")
        if any(token in lowered for token in ("contraseña", "password", "secret", "api key", "token")):
            risk_flags.append("credential_request")
        confidence = min(0.95, 0.55 + min(domain_score, 3) * 0.10)
        if intent == "greeting":
            confidence = 0.95
        elif domain == "trading" and market_instrument and market_timeframe:
            confidence = 0.95
        elif domain == "trading" and market_signal >= 2:
            confidence = max(confidence, 0.85)

        return CognitiveFrame(
            input_text=original_message,
            language=language,
            domain=domain,
            intent=intent,
            evidence_required=evidence_required,
            evidence_available=bool(context.get("evidence_available")),
            confidence=confidence,
            plan=self._plan(domain, evidence_required),
            risk_flags=risk_flags,
        )

    def decide(self, frame: CognitiveFrame, context: dict[str, Any]) -> dict[str, Any]:
        action = "respond"
        if frame.risk_flags:
            action = "respond_with_guardrails"
        if frame.evidence_required and not frame.evidence_available and frame.intent != "greeting":
            action = "request_or_retrieve_evidence"
        return {
            "action": action,
            "domain": frame.domain,
            "intent": frame.intent,
            "confidence": frame.confidence,
            "risk_flags": frame.risk_flags,
            "module": self._module_for(frame.domain),
            "execution_allowed": frame.domain != "trading" or "financial_action" not in frame.risk_flags,
        }

    def run(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {})
        frame = self.perceive(text, ctx)
        decision = self.decide(frame, ctx)
        return {"frame": frame.as_dict(), "decision": decision}

    def _domain(self, text: str) -> tuple[str, int]:
        lowered = text.lower()
        scores = {domain: sum(1 for hint in hints if hint in lowered) for domain, hints in self.DOMAIN_HINTS.items()}
        domain = max(scores, key=scores.get) if scores and max(scores.values()) else "general"
        return domain, scores.get(domain, 0)

    @staticmethod
    def _intent(text: str, domain: str) -> str:
        lowered = text.strip().lower()
        if re.fullmatch(r"(?:hola|holaa+|buenas|hey|hello|hi|oi|olá|ola|buenos días|buenas tardes|buenas noches|buenos dias|buenas tardes|buenas noches)[!.?,\s]*", lowered, re.I):
            return "greeting"
        if domain == "weather":
            return "weather_request"
        if domain == "trading":
            return "trading_request"
        if domain == "research":
            return "research_request"
        if domain == "programming":
            return "programming_request"
        if domain == "support":
            return "support_request"
        if domain == "marketing":
            return "marketing_request"
        if domain == "health":
            return "health_request"
        return "answer_or_assist"

    @staticmethod
    def _language(text: str, context: dict[str, Any]) -> str:
        explicit = str(context.get("language") or "").lower()
        spanish = {
            "qué", "cómo", "quiero", "puede", "necesito", "enfermedad", "afecta", "afectan", "síntoma",
            "síntomas", "tratamiento", "médico", "médica", "diagnóstico", "infección", "cáncer", "los", "las", "del", "una",
        }
        portuguese = {
            "que", "como", "quero", "pode", "preciso", "doença", "afeta", "sintoma", "sintomas", "tratamento",
            "médico", "médica", "diagnóstico", "infecção", "câncer", "os", "as", "dos", "uma", "não",
        }
        english = {"what", "how", "want", "can", "please", "disease", "symptom", "treatment", "diagnosis", "the"}
        tokens = set(re.findall(r"[\wÀ-ÿ]+", text.lower()))
        es_score = sum(token in spanish for token in tokens)
        pt_score = sum(token in portuguese for token in tokens)
        en_score = sum(token in english for token in tokens)
        if es_score >= 2 and es_score > pt_score:
            return "es"
        if pt_score >= 2 and pt_score > es_score:
            return "pt"
        if en_score >= 2 and en_score > max(es_score, pt_score):
            return "en"
        if explicit in {"es", "pt", "en"}:
            return explicit
        return "unknown"

    @staticmethod
    def _plan(domain: str, evidence_required: bool) -> list[str]:
        plan = ["perceive", "infer_intent", "check_context"]
        if evidence_required:
            plan.append("retrieve_or_validate_evidence")
        if domain != "general":
            plan.append("resolve_specialized_capability")
        if domain == "weather":
            plan.append("synthesize_weather_evidence")
        plan.extend(("evaluate_risk", "decide", "generate_response", "learn_from_outcome"))
        return plan

    @staticmethod
    def _module_for(domain: str) -> str | None:
        return {
            "weather": "weather",
            "trading": "sbt",
            "support": "bitefixes",
            "programming": "code_reasoning",
            "marketing": "marketing",
            "research": "research",
            "health": "health_reasoning",
        }.get(domain)
