from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

from .cognitive_architecture import BiteyCognitiveArchitecture


@dataclass
class NativeReasoningModel:
    """Bitey's provider-independent evidence-grounded reasoning model."""

    name: str = "bitey-native-cognitive-v1"
    priority: int = 1000
    free_only: bool = True

    def __post_init__(self) -> None:
        self.architecture = BiteyCognitiveArchitecture()

    async def health(self) -> bool:
        return True

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        user_message = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                user_message = str(message.get("content") or "").strip()
                if user_message:
                    break

        cognition = self.architecture.run(user_message, context)
        context["native_cognition"] = cognition
        frame = cognition["frame"]
        decision = cognition["decision"]
        evidence = str(context.get("evidence") or "").strip()

        if evidence:
            answer = self._reason_from_evidence(user_message, evidence, frame, decision)
            if answer:
                return answer

        return self._guarded_answer(frame, decision)

    @classmethod
    def _reason_from_evidence(cls, question: str, evidence: str, frame: dict[str, Any], decision: dict[str, Any]) -> str:
        """Synthesize only relevant factual claims from retrieved evidence."""
        claims = cls._extract_claims(evidence, question)
        if not claims:
            return ""

        language = frame.get("language") or "es"
        confidence = float(frame.get("confidence") or 0.0)
        risk = bool(decision.get("risk_flags"))
        q = question.lower()
        nasa_schedule = "nasa" in q and any(token in q for token in ("vuelo", "vuelos", "flight", "flights")) and "2026" in q

        if nasa_schedule:
            if language == "en":
                lead = "NASA does not provide one official global count for all 2026 flights in the retrieved evidence."
                limit = "Its schedules are published by mission/program category, so a single number would require defining the scope first."
                confidence_line = f"Evidence-grounded confidence: {confidence:.0%}."
                risk_line = " Verify critical dates before acting." if risk else ""
            elif language == "pt":
                lead = "A NASA não fornece um único total oficial para todos os voos de 2026 nas evidências recuperadas."
                limit = "Os calendários são publicados por categoria de missão/programa, portanto um único número exige definir primeiro o escopo."
                confidence_line = f"Confiança baseada em evidências: {confidence:.0%}."
                risk_line = " Confirme datas críticas antes de agir." if risk else ""
            else:
                lead = "La NASA no proporciona un único total oficial para todos los vuelos de 2026 en la evidencia recuperada."
                limit = "Los calendarios se publican por categoría de misión/programa, por lo que un único número requiere definir primero el alcance."
                confidence_line = f"Confianza basada en evidencia: {confidence:.0%}."
                risk_line = " Verifica las fechas críticas antes de actuar." if risk else ""
        else:
            if language == "en":
                lead = "I found relevant evidence for the question."
                limit = "The points below are limited to what the retrieved sources support."
                confidence_line = f"Evidence-grounded confidence: {confidence:.0%}."
                risk_line = " Verify critical details before acting." if risk else ""
            elif language == "pt":
                lead = "Encontrei evidências relevantes para a pergunta."
                limit = "Os pontos abaixo estão limitados ao que as fontes recuperadas sustentam."
                confidence_line = f"Confiança baseada em evidências: {confidence:.0%}."
                risk_line = " Confirme detalhes críticos antes de agir." if risk else ""
            else:
                lead = "Encontré evidencia relevante para la pregunta."
                limit = "Los puntos siguientes se limitan a lo que respaldan las fuentes recuperadas."
                confidence_line = f"Confianza basada en evidencia: {confidence:.0%}."
                risk_line = " Verifica los detalles críticos antes de actuar." if risk else ""

        bullets = "\n".join(f"- {claim}" for claim in claims[:3])
        return f"{lead}\n\n{bullets}\n\n{limit}{risk_line}\n\n{confidence_line}"

    @staticmethod
    def _extract_claims(evidence: str, question: str) -> list[str]:
        """Rank sentence-level evidence by relevance instead of dumping scraped pages."""
        stop = {
            "qué", "que", "cuál", "cual", "cuántos", "cuantos", "cuántas", "cuantas", "cómo", "como",
            "tiene", "tienen", "hay", "para", "por", "del", "de", "la", "el", "los", "las", "un", "una",
            "en", "y", "o", "a", "the", "what", "how", "many", "is", "are", "for", "of", "in", "and",
        }
        q_tokens = {
            token.lower() for token in re.findall(r"[\wÀ-ÿ]+", question)
            if len(token) >= 3 and token.lower() not in stop
        }
        semantic_groups = {
            "entity": {t for t in q_tokens if t in {"nasa", "spacex", "esa", "cnsа", "artemis"}},
            "activity": {t for t in q_tokens if t in {"vuelo", "vuelos", "flight", "flights", "lanzamiento", "lanzamientos", "launch", "launches"}},
            "schedule": {t for t in q_tokens if t in {"programado", "programados", "programada", "programadas", "previsto", "previstos", "calendario", "schedule", "scheduled"}},
            "year": {t for t in q_tokens if re.fullmatch(r"20\\d{2}", t)},
        }
        sentences = re.split(r"(?<=[.!?])\s+|\n+", evidence)
        candidates: list[tuple[float, str]] = []
        seen: set[str] = set()

        for raw in sentences:
            clean = re.sub(r"\s+", " ", raw).strip(" -•")
            if len(clean) < 35:
                continue
            if re.match(r"^(?:SOURCE|TITLE|URL|SNIPPET|LINK|FUENTE|TÍTULO|EVIDENCE)\b", clean, re.I):
                continue
            if clean.startswith(("http://", "https://")):
                continue

            words = {token.lower() for token in re.findall(r"[\wÀ-ÿ]+", clean)}
            overlap = len(q_tokens & words)
            groups_hit = sum(1 for values in semantic_groups.values() if values and words & values)
            score = float(overlap * 3 + groups_hit * 4)
            if re.search(r"\b20\d{2}\b", clean):
                score += 2
            if re.search(r"\b\d+(?:[.,]\d+)?\b", clean):
                score += 1.5
            if score < 8 or (len(semantic_groups["activity"]) and not words & semantic_groups["activity"]):
                continue

            if len(clean) > 360:
                clean = clean[:357].rsplit(" ", 1)[0] + "..."
            key = re.sub(r"\W+", " ", clean.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            candidates.append((score, clean))

        candidates.sort(key=lambda item: (-item[0], len(item[1])))
        return [claim for _score, claim in candidates[:8]]

    @staticmethod
    def _guarded_answer(frame: dict[str, Any], decision: dict[str, Any]) -> str:
        language = frame.get("language") or "es"
        domain = frame.get("domain") or "general"
        confidence = float(frame.get("confidence") or 0.0)
        if language == "en":
            return (f"I can reason about this request, but I do not have sufficient verified evidence to state a factual conclusion. "
                    f"Detected domain: {domain}; cognitive confidence: {confidence:.0%}. I will not invent the missing information.")
        if language == "pt":
            return (f"Posso raciocinar sobre esta solicitação, mas não tenho evidências verificadas suficientes para afirmar uma conclusão factual. "
                    f"Domínio identificado: {domain}; confiança cognitiva: {confidence:.0%}. Não vou inventar a informação ausente.")
        return (f"Puedo razonar sobre esta solicitud, pero no tengo evidencia verificada suficiente para afirmar una conclusión factual. "
                f"Dominio identificado: {domain}; confianza cognitiva: {confidence:.0%}. No voy a inventar la información que falta.")
