from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NativeReasoningModel:
    """Deterministic, dependency-free reasoning model.

    This is intentionally not presented as a neural LLM. It is Bitey's
    independent cognitive fallback: it can classify intent, use supplied
    evidence/context, explain limitations, and keep the service operational
    when every external model is unavailable.
    """

    name: str = "bitey-native-cognitive-v1"
    priority: int = 1000
    free_only: bool = True

    async def health(self) -> bool:
        return True

    async def generate(self, *, messages: list[dict[str, str]], context: dict[str, Any]) -> str:
        user_message = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                user_message = str(message.get("content") or "").strip()
                if user_message:
                    break

        cognition = context.get("cognition") or {}
        intention = cognition.get("intention") or {}
        domain = str(intention.get("domain") or "general")
        confidence = float(cognition.get("confidence") or 0.0)
        evidence = bool((cognition.get("evidence") or {}).get("available"))
        language = str((cognition.get("perception") or {}).get("language_hint") or "unknown")

        if language == "pt":
            return self._portuguese(user_message, domain, confidence, evidence)
        if language == "en":
            return self._english(user_message, domain, confidence, evidence)
        return self._spanish(user_message, domain, confidence, evidence)

    @staticmethod
    def _spanish(message: str, domain: str, confidence: float, evidence: bool) -> str:
        evidence_line = "Hay evidencia recuperada que debe guiar la respuesta." if evidence else "No se ha recuperado evidencia externa; no voy a inventarla."
        if domain == "trading":
            return (
                "Bitey Native Cognitive v1 está activo como modelo independiente.\n\n"
                f"He identificado la solicitud como **trading** con confianza cognitiva de {confidence:.0%}. "
                "La arquitectura mantiene el análisis separado de cualquier ejecución de órdenes.\n\n"
                f"{evidence_line}\n\n"
                f"Solicitud recibida: {message}"
            )
        if domain == "programming":
            return (
                "Bitey Native Cognitive v1 está activo como modelo independiente.\n\n"
                f"La solicitud fue clasificada como **programación** ({confidence:.0%}). "
                "Puedo razonar sobre estructura, errores y próximos pasos sin ejecutar código arbitrario.\n\n"
                f"{evidence_line}"
            )
        if domain == "research":
            return (
                "Bitey Native Cognitive v1 está activo como modelo independiente.\n\n"
                f"La solicitud requiere **investigación** ({confidence:.0%}). {evidence_line}"
            )
        return (
            "Bitey Native Cognitive v1 está activo como capa cognitiva independiente.\n\n"
            f"He interpretado la solicitud como **{domain}** con confianza de {confidence:.0%}. "
            f"{evidence_line}\n\n"
            "Cuando haya un modelo externo gratuito disponible, Bitey puede delegar la generación a ese modelo y conservar esta capa como respaldo."
        )

    @staticmethod
    def _portuguese(message: str, domain: str, confidence: float, evidence: bool) -> str:
        evidence_line = "Há evidência recuperada que deve orientar a resposta." if evidence else "Nenhuma evidência externa foi recuperada; não vou inventá-la."
        return (
            "Bitey Native Cognitive v1 está ativo como modelo independente.\n\n"
            f"Solicitação classificada como **{domain}** ({confidence:.0%}). {evidence_line}\n\n"
            "Quando houver um modelo externo gratuito disponível, Bitey pode usá-lo e manter esta camada como fallback."
        )

    @staticmethod
    def _english(message: str, domain: str, confidence: float, evidence: bool) -> str:
        evidence_line = "Retrieved evidence is available and should guide the answer." if evidence else "No external evidence was retrieved; I will not invent it."
        return (
            "Bitey Native Cognitive v1 is active as an independent model.\n\n"
            f"The request was classified as **{domain}** ({confidence:.0%}). {evidence_line}\n\n"
            "When a free external model is available, Bitey can delegate generation to it while keeping this layer as a fallback."
        )
