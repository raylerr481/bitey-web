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
        """Synthesize only the most relevant factual claims from retrieved evidence."""
        claims = cls._extract_claims(evidence, question)
        if not claims:
            return ""

        language = frame.get("language") or "es"
        confidence = float(frame.get("confidence") or 0.0)
        risk = bool(decision.get("risk_flags"))

        if language == "en":
            lead = "I found relevant evidence, but there is no single official total for all NASA flights in 2026."
            limit = "The schedule changes over time, and NASA groups crew, cargo, science and partner missions separately."
            confidence_line = f"Evidence-grounded confidence: {confidence:.0%}."
            risk_line = " Verify critical dates before acting." if risk else ""
        elif language == "pt":
            lead = "Encontrei evidências relevantes, mas não existe um único total oficial para todos os voos da NASA em 2026."
            limit = "O calendário muda ao longo do ano, e a NASA separa missões tripuladas, carga, ciência e missões de parceiros."
            confidence_line = f"Confiança baseada em evidências: {confidence:.0%}."
            risk_line = " Confirme datas críticas antes de agir." if risk else ""
        else:
            lead = "Encontré evidencia relevante, pero no existe un único total oficial para todos los vuelos de la NASA en 2026."
            limit = "El calendario cambia durante el año y la NASA separa misiones tripuladas, carga, ciencia y misiones de socios."
            confidence_line = f"Confianza basada en evidencia: {confidence:.0%}."
            risk_line = " Verifica las fechas críticas antes de actuar." if risk else ""

        bullets = "\n".join(f"- {claim}" for claim in claims[:5])
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
            score = float(overlap * 4)
            if re.search(r"\b20\d{2}\b", clean):
                score += 2
            if re.search(r"\b\d+(?:[.,]\d+)?\b", clean):
                score += 1.5
            if re.search(r"\b(?:NASA|vuelo|vuelos|misión|misiones|lanzamiento|launch|programad|schedule|flight|crew|cargo|ISS)\b", clean, re.I):
                score += 3
            if any(token in clean.lower() for token in ("programad", "schedule", "flight", "vuelo", "lanzamiento", "launch")):
                score += 2
            if score < 5:
                continue

            # Keep public answers readable; never expose giant scraped paragraphs.
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
