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
        """Produce a deterministic synthesis from retrieved evidence when no LLM is available.

        This is deliberately not a fake LLM: it extracts factual claims from the
        research payload, removes source metadata, deduplicates them, and states
        the evidentiary limit explicitly instead of inventing missing facts.
        """
        claims = cls._extract_claims(evidence)
        if not claims:
            return ""

        language = frame.get("language") or "es"
        confidence = float(frame.get("confidence") or 0.0)
        risk = bool(decision.get("risk_flags"))
        if language == "en":
            lead = "Based on the evidence retrieved by Bitey, the supported conclusion is:"
            limit = "The available evidence is not sufficient to establish facts beyond these points."
            risk_line = " Because this involves a potentially sensitive action, verify the critical details before acting." if risk else ""
        elif language == "pt":
            lead = "Com base nas evidências recuperadas pelo Bitey, a conclusão sustentada é:"
            limit = "As evidências disponíveis não são suficientes para afirmar fatos além destes pontos."
            risk_line = " Como isso pode envolver uma ação sensível, confirme os detalhes críticos antes de agir." if risk else ""
        else:
            lead = "Con base en la evidencia recuperada por Bitey, la conclusión que sí está respaldada es:"
            limit = "La evidencia disponible no permite afirmar hechos más allá de estos puntos."
            risk_line = " Como puede implicar una acción sensible, verifica los datos críticos antes de actuar." if risk else ""

        bullets = "\n".join(f"- {claim}" for claim in claims[:6])
        if language == "en":
            confidence_line = f"Evidence-grounded confidence: {confidence:.0%}."
        elif language == "pt":
            confidence_line = f"Confiança baseada em evidências: {confidence:.0%}."
        else:
            confidence_line = f"Confianza basada en evidencia: {confidence:.0%}."
        return f"{lead}\n\n{bullets}\n\n{limit}{risk_line}\n\n{confidence_line}"

    @staticmethod
    def _extract_claims(evidence: str) -> list[str]:
        chunks = re.split(r"\n\s*\n+", evidence)
        claims: list[str] = []
        seen: set[str] = set()
        for chunk in chunks:
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            useful: list[str] = []
            for line in lines:
                if re.match(r"^(?:SOURCE|TITLE|URL|SNIPPET|LINK|FUENTE|TÍTULO)\b", line, re.I):
                    continue
                if line.startswith(("http://", "https://")):
                    continue
                clean = re.sub(r"\s+", " ", line).strip(" -•")
                if len(clean) >= 24:
                    useful.append(clean)
            sentence = " ".join(useful)
            if len(sentence) < 24:
                continue
            key = re.sub(r"\W+", " ", sentence.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            claims.append(sentence)
        return claims

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
