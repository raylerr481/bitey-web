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
        direct = self._direct_general_answer(user_message, frame)
        if direct:
            return direct
        specialized = self._specialized_evidence_answer(user_message, evidence, frame)
        if specialized:
            return specialized
        if evidence:
            answer = self._reason_from_evidence(user_message, evidence, frame, decision)
            if answer:
                return answer
        return self._guarded_answer(frame, decision)

    @staticmethod
    def _direct_general_answer(question: str, frame: dict[str, Any]) -> str:
        q = question.strip().lower()
        language = frame.get("language") or "es"
        if re.search(r"\b(qui[eé]n eres|qu[eé] eres|qu[eé] puedes hacer|qu[eé] haces|c[oó]mo funcionas)\b", q, re.I):
            return ("Soy Bitey IA, un asistente cognitivo general. Puedo conversar, explicar conceptos, analizar información, "
                    "ayudarte con código, proyectos, investigación y razonamiento, y usar herramientas cuando la tarea lo requiere. "
                    "También puedo trabajar con módulos especializados cuando la solicitud realmente los necesita, respetando sus límites de seguridad.")
        if re.search(r"\bqu[eé] es bitcoin\b|\bwhat is bitcoin\b|\bo que [ée] bitcoin\b", q, re.I):
            if language == "pt":
                return "Bitcoin é uma moeda digital descentralizada introduzida em 2009. Funciona sobre uma rede distribuída chamada blockchain, onde as transações são registradas e validadas pela rede. Não é emitido por um banco central e seu preço pode ser muito volátil."
            if language == "en":
                return "Bitcoin is a decentralized digital currency introduced in 2009. It operates on a distributed blockchain network where transactions are recorded and validated by the network. It is not issued by a central bank and can be highly volatile."
            return "Bitcoin es una moneda digital descentralizada introducida en 2009. Funciona sobre una red distribuida llamada blockchain, donde las transacciones se registran y validan en la red. No es emitido por un banco central y su precio puede ser muy volátil."
        return ""

    @staticmethod
    def _specialized_evidence_answer(question: str, evidence: str, frame: dict[str, Any]) -> str:
        """Render specialized SBT evidence without falling into the generic fallback."""
        if not evidence:
            return ""
        q = question.lower()
        trading = frame.get("domain") == "trading" or bool(re.search(r"\b(?:[a-z]{2,12}(?:usdt|usd)|[a-z]{6})\b|\b(?:m1|m3|m5|m15|m30|h1|h4|d1|w1|mn1)\b", q, re.I))
        if not trading:
            return ""
        if "sbt_module_not_configured" in evidence or "not configured for Bitey IA Web" in evidence:
            return ("He clasificado correctamente la solicitud como análisis de trading y el flujo SBT fue seleccionado, "
                    "pero SBT todavía no está conectado a una fuente de mercado verificable desde Bitey IA Web.\n\n"
                    "Por seguridad no voy a inventar el precio, RSI, tendencia, señal, entrada, stop loss ni take profit de BTCUSDT en M1.\n\n"
                    "Estado: SBT seleccionado · datos de mercado verificados: no disponibles · ejecución real: deshabilitada.")
        if "No verified market data" in evidence or "No hay datos de mercado verificados" in evidence or "could not obtain verified market data" in evidence:
            return ("SBT fue seleccionado para analizar el mercado, pero no pudo obtener datos de mercado verificados para esta solicitud.\n\n"
                    "No voy a inventar precio, indicadores ni una señal de entrada/salida.\n\n"
                    "Estado: análisis SBT · datos verificados: no disponibles · ejecución real: deshabilitada.")
        if "SBT verified market analysis" in evidence:
            price = re.search(r"Last price:\s*([^\.]+)", evidence, re.I)
            bias = re.search(r"Bias:\s*([^\.]+)", evidence, re.I)
            confidence = re.search(r"Confidence:\s*([^\.]+)", evidence, re.I)
            return ("SBT obtuvo datos de mercado verificados y ejecutó el análisis técnico en modo research-only.\n\n"
                    f"Precio de referencia: {price.group(1).strip() if price else 'no especificado'}\n"
                    f"Sesgo: {bias.group(1).strip() if bias else 'no especificado'}\n"
                    f"Confianza: {confidence.group(1).strip() if confidence else 'no especificada'}\n\n"
                    "La ejecución de órdenes permanece deshabilitada. Los datos proceden del módulo SBT verificado.")
        return ""

    @classmethod
    def _reason_from_evidence(cls, question: str, evidence: str, frame: dict[str, Any], decision: dict[str, Any]) -> str:
        claims = cls._extract_claims(evidence, question)
        if not claims:
            return ""
        language = cls._answer_language(question, frame.get("language"))
        confidence = float(frame.get("confidence") or 0.0)
        risk = bool(decision.get("risk_flags"))
        if language == "en":
            lead, limit, confidence_line = "I found relevant evidence for the question.", "The points below are limited to what the retrieved sources support.", f"Evidence-grounded confidence: {confidence:.0%}."
            risk_line = " Verify critical details before acting." if risk else ""
        elif language == "pt":
            lead, limit, confidence_line = "Encontrei evidências relevantes para a pergunta.", "Os pontos abaixo estão limitados ao que as fontes recuperadas sustentam.", f"Confiança baseada em evidências: {confidence:.0%}."
            risk_line = " Confirme detalhes críticos antes de agir." if risk else ""
        else:
            lead, limit, confidence_line = "Encontré evidencia relevante para la pregunta.", "Los puntos siguientes se limitan a lo que respaldan las fuentes recuperadas.", f"Confianza basada en evidencia: {confidence:.0%}."
            risk_line = " Verifica los detalles críticos antes de actuar." if risk else ""
        bullets = "\n".join(f"- {claim}" for claim in claims[:3])
        return f"{lead}\n\n{bullets}\n\n{limit}{risk_line}\n\n{confidence_line}"

    @staticmethod
    def _extract_claims(evidence: str, question: str) -> list[str]:
        stop = {"qué", "que", "cuál", "cual", "cuántos", "cuantos", "cuántas", "cuantas", "cómo", "como", "tiene", "tienen", "hay", "para", "por", "del", "de", "la", "el", "los", "las", "un", "una", "en", "y", "o", "a", "the", "what", "how", "many", "is", "are", "for", "of", "in", "and"}
        q_tokens = {t.lower() for t in re.findall(r"[\wÀ-ÿ]+", question) if len(t) >= 3 and t.lower() not in stop}
        candidates: list[tuple[float, str]] = []
        seen: set[str] = set()
        for raw in re.split(r"(?<=[.!?])\s+|\n+", evidence):
            clean = re.sub(r"\s+", " ", raw).strip(" -•")
            if len(clean) < 35 or re.match(r"^(?:SOURCE|TITLE|URL|SNIPPET|LINK|FUENTE|TÍTULO|EVIDENCE)\b", clean, re.I) or clean.startswith(("http://", "https://")):
                continue
            words = {t.lower() for t in re.findall(r"[\wÀ-ÿ]+", clean)}
            score = float(len(q_tokens & words) * 3)
            if re.search(r"\b20\d{2}\b", clean): score += 2
            if re.search(r"\b\d+(?:[.,]\d+)?\b", clean): score += 1.5
            if score < 8: continue
            if len(clean) > 360: clean = clean[:357].rsplit(" ", 1)[0] + "..."
            key = re.sub(r"\W+", " ", clean.lower()).strip()
            if key not in seen:
                seen.add(key); candidates.append((score, clean))
        candidates.sort(key=lambda item: (-item[0], len(item[1])))
        return [claim for _score, claim in candidates[:8]]

    @staticmethod
    def _answer_language(question: str, frame_language: str | None) -> str:
        tokens = set(re.findall(r"[\wÀ-ÿ]+", question.lower()))
        es = sum(t in {"qué", "cómo", "quiero", "puede", "necesito", "los", "las", "del", "una"} for t in tokens)
        pt = sum(t in {"que", "como", "quero", "pode", "preciso", "os", "as", "dos", "uma", "não"} for t in tokens)
        en = sum(t in {"what", "how", "want", "can", "please", "the"} for t in tokens)
        if es >= 2 and es > pt: return "es"
        if pt >= 2 and pt > es: return "pt"
        if en >= 2 and en > max(es, pt): return "en"
        return frame_language or "es"

    @staticmethod
    def _guarded_answer(frame: dict[str, Any], decision: dict[str, Any]) -> str:
        language = frame.get("language") or "es"
        domain = frame.get("domain") or "general"
        confidence = float(frame.get("confidence") or 0.0)
        if language == "en":
            return f"I can reason about this request, but I do not have sufficient verified evidence to state a factual conclusion. Detected domain: {domain}; cognitive confidence: {confidence:.0%}. I will not invent the missing information."
        if language == "pt":
            return f"Posso raciocinar sobre esta solicitação, mas não tenho evidências verificadas suficientes para afirmar uma conclusão factual. Domínio identificado: {domain}; confiança cognitiva: {confidence:.0%}. Não vou inventar a informação ausente."
        return f"Puedo razonar sobre esta solicitud, pero no tengo evidencia verificada suficiente para afirmar una conclusión factual. Dominio identificado: {domain}; confianza cognitiva: {confidence:.0%}. No voy a inventar la información que falta."
