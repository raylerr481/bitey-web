from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cognitive_architecture import BiteyCognitiveArchitecture


@dataclass
class NativeReasoningModel:
    """Bitey's provider-independent deterministic cognitive model."""

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
        frame = cognition["frame"]
        decision = cognition["decision"]
        # Keep the canonical cognitive state available to downstream learning.
        context["native_cognition"] = cognition
        domain = frame["domain"]
        confidence = float(frame["confidence"])
        language = frame["language"]
        evidence = bool(frame["evidence_available"])

        if language == "pt":
            return self._portuguese(domain, confidence, evidence, decision)
        if language == "en":
            return self._english(domain, confidence, evidence, decision)
        return self._spanish(domain, confidence, evidence, decision)

    @staticmethod
    def _spanish(domain: str, confidence: float, evidence: bool, decision: dict[str, Any]) -> str:
        evidence_line = "Hay evidencia disponible y debe guiar la respuesta." if evidence else "No hay evidencia externa disponible; no voy a inventarla."
        guard = " Se aplican controles antes de cualquier acción sensible." if decision["risk_flags"] else ""
        module = decision.get("module")
        module_line = f" Módulo candidato: **{module}**." if module else ""
        return (
            "Bitey Native Cognitive v1 está activo como modelo cognitivo independiente.\n\n"
            f"Dominio identificado: **{domain}** · confianza: **{confidence:.0%}**.{module_line}\n\n"
            f"{evidence_line}{guard}\n\n"
            "Bitey puede usar un LLM externo gratuito para mejorar la generación lingüística, pero la percepción, planificación, evaluación de riesgo y decisión pertenecen al núcleo cognitivo de Bitey."
        )

    @staticmethod
    def _portuguese(domain: str, confidence: float, evidence: bool, decision: dict[str, Any]) -> str:
        evidence_line = "Há evidência disponível e ela deve orientar a resposta." if evidence else "Não há evidência externa disponível; não vou inventá-la."
        return (
            "Bitey Native Cognitive v1 está ativo como modelo cognitivo independente.\n\n"
            f"Domínio identificado: **{domain}** · confiança: **{confidence:.0%}**. {evidence_line}\n\n"
            "Modelos externos gratuitos podem melhorar a geração de linguagem, mas a percepção, o planejamento, a avaliação de risco e a decisão pertencem ao núcleo cognitivo do Bitey."
        )

    @staticmethod
    def _english(domain: str, confidence: float, evidence: bool, decision: dict[str, Any]) -> str:
        evidence_line = "Evidence is available and should guide the answer." if evidence else "No external evidence is available; I will not invent it."
        return (
            "Bitey Native Cognitive v1 is active as an independent cognitive model.\n\n"
            f"Detected domain: **{domain}** · confidence: **{confidence:.0%}**. {evidence_line}\n\n"
            "Free external models may improve language generation, but perception, planning, risk evaluation and decision-making belong to Bitey's cognitive core."
        )
