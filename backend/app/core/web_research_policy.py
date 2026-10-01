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
        r"\b(precio|precios|cotización|cotizaciones|cotiza|stock|acciones|dividendo|dividendos|clima|temperatura|pronóstico|pronostico|weather|forecast|news|noticias|horario|horarios|disponible|disponibilidad|versión|version|release|regulación|regulacion|ley|impuesto|tax|tipo de cambio|exchange rate|población|poblacion|estadística|estadisticas|ranking|score|resultado|resultados)\b",
        re.I,
    )
    DYNAMIC_CONTEXT = re.compile(
        r"\b(?:mercado|mercados|tiempo|time|valor|valores)\b.*\b(?:ahora|hoy|actual|actualmente|precio|cotiza|cotización|cotizacion|en vivo|tiempo real|latest|current|live)\b"
        r"|\b(?:ahora|hoy|actual|actualmente|precio|cotiza|cotización|cotizacion|en vivo|tiempo real|latest|current|live)\b.*\b(?:mercado|mercados|tiempo|time|valor|valores)\b",
        re.I,
    )
    CONCEPTUAL = re.compile(
        r"^(?:\s*(?:¿|\?)?\s*)?(?:qué|que|cuál|cual|quién|quien|what|which|who)\s+"
        r"(?:es|son|significa|significan|are|is|means)\b",
        re.I,
    )
    FACTUAL_QUESTION = re.compile(
        r"(?:\?|\b(?:quién|quien|qué|que|cuál|cual|cuándo|cuando|dónde|donde|cómo|como|por qué|porque|cuánto|cuanto|cuántos|cuantos|qué significa|que significa|qué es|que es|what|who|which|when|where|how|why|how much|how many)\b)",
        re.I,
    )
    KNOWLEDGE_REQUEST = re.compile(
        r"\b(?:dime|decime|explícame|explicame|explique|informa(?:me|r)?|quiero saber|necesito saber|enséñame|ensename|muéstrame|muestrame|tell me|explain|inform me|i want to know|i need to know|teach me)\b",
        re.I,
    )
    CASUAL = re.compile(
        r"^(?:hola|hey|hi|buenas|buenos días|buenas tardes|buenas noches|cómo estás|como estas|qué tal|que tal|todo bien|gracias|muchas gracias|ok|vale|adiós|adios)[!?. ]*$",
        re.I,
    )
    MEDICAL = re.compile(
        r"\b(salud|health|enfermedad|enfermedades|disease|síntoma|síntomas|sintoma|sintomas|symptom|sida|vih|hiv|tratamiento|tratamientos|treatment|medicina|medical|médico|médica|diagnóstico|diagnostico|diagnosis|infección|infecciones|infection|cáncer|cancer|virus|bacteria|vacuna|vacunación|hospital|medicación|medicamento)\b",
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
        if self.FACTUAL_DYNAMIC.search(text) or self.DYNAMIC_CONTEXT.search(text):
            score += 0.72; reasons.append("dynamic_domain")
        if self.FACTUAL_QUESTION.search(text):
            score += 0.78; reasons.append("factual_question")
        if self.KNOWLEDGE_REQUEST.search(text):
            score += 0.78; reasons.append("knowledge_request")
        if self.MEDICAL.search(text):
            score += 0.90; reasons.append("medical_domain")
        if self.EVIDENCE.search(text):
            score += 0.80; reasons.append("evidence_requested")
        if self.URL.search(text):
            score += 0.95; reasons.append("url_present")

        # Stable conceptual questions should normally be answered directly.
        # Do not force them into web/evidence mode merely because they are
        # factual questions. Explicit research, freshness, dynamic data,
        # medical topics, URLs, and evidence requests still override this.
        conceptual = bool(self.CONCEPTUAL.search(text))
        protected_research_signal = bool(
            self.EXPLICIT.search(text)
            or self.FRESH.search(text)
            or self.FACTUAL_DYNAMIC.search(text)
            or self.DYNAMIC_CONTEXT.search(text)
            or self.EVIDENCE.search(text)
            or self.URL.search(text)
            or self.MEDICAL.search(text)
        )
        if conceptual and not protected_research_signal:
            score = 0.0
            reasons = ["stable_conceptual_knowledge"]

        if self.CASUAL.fullmatch(text):
            score = 0.0
            reasons = []

        research_ctx = ctx.get("research") if isinstance(ctx.get("research"), dict) else {}
        if research_ctx.get("requested") or research_ctx.get("requires_web_research") or research_ctx.get("needs_web") or research_ctx.get("freshness_required"):
            score += 1.0; reasons.append("cognitive_core_required_web")

        required = score >= 0.70
        strategy = "multi_source_research" if score >= 1.35 else ("web_lookup" if required else "none")
        confidence = min(1.0, score)
        if required:
            ctx["research_required"] = True
            research_state = ctx.setdefault("research", {})
            if isinstance(research_state, dict):
                research_state["requires_web_research"] = True
                research_state["needs_web"] = True
        return WebResearchDecision(required=required, confidence=confidence, reasons=list(dict.fromkeys(reasons)), strategy=strategy)
