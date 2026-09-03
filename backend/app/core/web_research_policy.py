from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(frozen=True)
class WebResearchDecision:
    required: bool
    confidence: float
    reasons: list[str] = field(default_factory=list)
    strategy: str = "none"


class WebResearchPolicy:
    """General policy deciding when an answer should acquire external web evidence."""

    EXPLICIT = re.compile(
        r"\b(busca|buscar|búsqueda|investiga|investigar|investigación|averigua|verifica|comprueba|confirma|fuentes|fuente|consulta|revisa|contrasta|search|research|verify|check|look up|find out)\b",
        re.I,
    )
    FRESH = re.compile(
        r"\b(actual|actualmente|ahora|ahora mismo|hoy|ayer|mañana|últim[oa]s?|reciente|recientemente|en vivo|tiempo real|202[0-9]|current|today|yesterday|tomorrow|latest|recent|live|real[- ]time)\b",
        re.I,
    )
    FACTUAL_DYNAMIC = re.compile(
        r"\b(precio|precios|cotización|cotizaciones|stock|acciones|mercado|clima|temperatura|tiempo|pronóstico|weather|forecast|news|noticias|horario|horarios|disponible|disponibilidad|versión|version|release|regulación|ley|impuesto|tax|tipo de cambio|exchange rate|población|estadística|ranking|score|resultado|resultados)\b",
        re.I,
    )
    EVIDENCE = re.compile(r"\b(fuente|fuentes|cita|citas|evidencia|evidence|source|sources|enlace|enlaces|link|links)\b", re.I)
    URL = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)

    def decide(self, message: str, context: dict[str, Any] | None = None) -> WebResearchDecision:
        text = (message or "").strip()
        ctx = context or {}
        reasons: list[str] = []
        score = 0.0

        if self.EXPLICIT.search(text):
            score += 0.95; reasons.append("explicit_research")
        if self.FRESH.search(text):
            score += 0.90; reasons.append("freshness_sensitive")
        if self.FACTUAL_DYNAMIC.search(text):
            score += 0.72; reasons.append("dynamic_domain")
        if self.EVIDENCE.search(text):
            score += 0.80; reasons.append("evidence_requested")
        if self.URL.search(text):
            score += 0.95; reasons.append("url_present")

        research_ctx = ctx.get("research") if isinstance(ctx.get("research"), dict) else {}
        if research_ctx.get("requested") or research_ctx.get("requires_web_research") or research_ctx.get("needs_web") or research_ctx.get("freshness_required"):
            score += 1.0; reasons.append("cognitive_core_required_web")

        # Avoid treating every generic question as a web task. Explicit requests,
        # freshness, URLs, evidence, or dynamic domains are sufficient signals.
        required = score >= 0.70
        strategy = "multi_source_research" if score >= 1.35 else ("web_lookup" if required else "none")
        confidence = min(1.0, score)
        return WebResearchDecision(required=required, confidence=confidence, reasons=list(dict.fromkeys(reasons)), strategy=strategy)
