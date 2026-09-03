from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import hashlib
import re


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
        "trading": ("trading", "trade", "forex", "stock", "mercado", "mt5", "tradingview", "bot", "bolsa"),
        "support": ("ticket", "soporte", "error", "incidencia", "cliente", "reparación", "repair", "cctv"),
        "programming": ("código", "codigo", "python", "javascript", "api", "bug", "programar", "github"),
        "marketing": ("marketing", "ventas", "campaña", "publicidad", "seo", "cliente"),
        "research": ("investiga", "investigar", "research", "evidencia", "fuentes", "estudio", "analiza"),
    }

    def perceive(self, text: str, context: dict[str, Any]) -> CognitiveFrame:
        message = text.strip()
        language = self._language(message, context)
        domain, domain_score = self._domain(message)
        evidence_required = bool(context.get("research")) or domain == "research"
        risk_flags: list[str] = []
        lowered = message.lower()
        if domain == "trading" and any(token in lowered for token in ("comprar", "vender", "ejecuta", "orden", "live", "real")):
            risk_flags.append("financial_action")
        if any(token in lowered for token in ("contraseña", "password", "secret", "api key", "token")):
            risk_flags.append("credential_request")
        confidence = min(0.95, 0.55 + min(domain_score, 3) * 0.10)
        return CognitiveFrame(
            input_text=message,
            language=language,
            domain=domain,
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
        if frame.evidence_required and not frame.evidence_available:
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
    def _language(text: str, context: dict[str, Any]) -> str:
        explicit = str(context.get("language") or "").lower()
        if explicit in {"es", "pt", "en"}:
            return explicit
        lowered = f" {text.lower()} "
        if any(token in lowered for token in (" qué ", " cómo ", " quiero ", " para ", " puede ", " necesito ")):
            return "es"
        if any(token in lowered for token in (" que ", " como ", " quero ", " para ", " pode ", " preciso ")):
            return "pt"
        if any(token in lowered for token in (" what ", " how ", " want ", " can ", " please ")):
            return "en"
        return "unknown"

    @staticmethod
    def _plan(domain: str, evidence_required: bool) -> list[str]:
        plan = ["perceive", "infer_intent", "check_context"]
        if evidence_required:
            plan.append("retrieve_or_validate_evidence")
        if domain != "general":
            plan.append("resolve_specialized_capability")
        plan.extend(("evaluate_risk", "decide", "generate_response", "learn_from_outcome"))
        return plan

    @staticmethod
    def _module_for(domain: str) -> str | None:
        return {"trading": "sbt", "support": "bitefixes", "programming": "code_reasoning", "marketing": "marketing", "research": "research"}.get(domain)
