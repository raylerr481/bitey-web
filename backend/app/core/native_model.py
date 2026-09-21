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
        # Substantive requests must honor evidence-first research; direct deterministic answers are conversational-only fallbacks.
        direct = self._direct_general_answer(user_message, frame) if not bool(context.get("evidence_required") or context.get("research_required")) else ""
        if direct: return direct
        specialized = self._specialized_evidence_answer(user_message, evidence, frame)
        if specialized: return specialized
        if evidence:
            answer = self._reason_from_evidence(user_message, evidence, frame, decision)
            if answer: return answer
        return self._contextual_guarded_answer(user_message, frame, decision, context)

    @staticmethod
    def _direct_general_answer(question: str, frame: dict[str, Any]) -> str:
        q = question.strip().lower(); language = frame.get("language") or "es"; intent = str(frame.get("intent") or "")
        if intent == "greeting":
            if language == "pt": return "Olá! Sou Bitey IA. Como posso ajudar você hoje?"
            if language == "en": return "Hello! I'm Bitey IA. How can I help you today?"
            return "¡Hola! Soy Bitey IA. ¿Cómo puedo ayudarte hoy?"
        if re.search(r"\b(qui[eé]n eres|qu[eé] eres|qu[eé] puedes hacer|qu[eé] haces|c[oó]mo funcionas)\b", q, re.I):
            return ("Soy Bitey IA, un asistente cognitivo general. Puedo conversar, explicar conceptos, analizar información, "
                    "ayudarte con código, proyectos, investigación y razonamiento, y usar herramientas cuando la tarea lo requiere. "
                    "También puedo trabajar con módulos especializados cuando la solicitud realmente los necesita, respetando sus límites de seguridad.")
        if re.search(r"\bqu[eé] es bitcoin\b|\bwhat is bitcoin\b|\bo que [ée] bitcoin\b", q, re.I):
            if language == "pt": return "Bitcoin é uma moeda digital descentralizada introduzida em 2009. Funciona sobre uma rede distribuída chamada blockchain, onde as transações são registradas e validadas pela rede. Não é emitido por um banco central e seu preço pode ser muito volátil."
            if language == "en": return "Bitcoin is a decentralized digital currency introduced in 2009. It operates on a distributed blockchain network where transactions are recorded and validated by the network. It is not issued by a central bank and can be highly volatile."
            return "Bitcoin es una moneda digital descentralizada introducida en 2009. Funciona sobre una red distribuida llamada blockchain, donde las transacciones se registran y validan en la red. No es emitido por un banco central y su precio puede ser muy volátil."
        concept = re.match(r"^(?:[¿?]\s*)?(?:qué|que|cuál|cual|cómo|como)\s+(?:es|son|significa|funciona)\s+(.+?)[?¿!¡.\s]*$", q, re.I)
        if concept:
            subject = re.sub(r"\s+", " ", concept.group(1)).strip(" ?¿!¡.")
            definitions = {
                "mercado": {
                    "es": "Un mercado es un sistema o espacio donde compradores y vendedores intercambian bienes, servicios o activos y donde la oferta y la demanda ayudan a formar precios.",
                    "pt": "Um mercado é um sistema ou espaço onde compradores e vendedores trocam bens, serviços ou ativos, e a oferta e a demanda ajudam a formar preços.",
                    "en": "A market is a system or place where buyers and sellers exchange goods, services, or assets, with supply and demand helping determine prices.",
                },
                "mercado financiero": {
                    "es": "El mercado financiero reúne mercados e instituciones donde se negocian activos como acciones, bonos y divisas. Ayuda a canalizar capital, formar precios y gestionar riesgos.",
                    "pt": "O mercado financeiro reúne mercados e instituições onde são negociados ativos como ações, títulos e moedas. Ele ajuda a canalizar capital, formar preços e administrar riscos.",
                    "en": "The financial market is the set of markets and institutions where assets such as stocks, bonds, and currencies are traded. It helps channel capital, form prices, and manage risk.",
                },
                "trading": {
                    "es": "Trading es la compra y venta de activos financieros para buscar aprovechar movimientos de precio. Puede involucrar acciones, divisas, criptomonedas e índices y siempre implica riesgo de pérdida.",
                    "pt": "Trading é a compra e venda de ativos financeiros buscando aproveitar movimentos de preço. Pode envolver ações, câmbio, criptomoedas e índices e sempre envolve risco de perda.",
                    "en": "Trading is the buying and selling of financial assets to seek gains from price movements. It can involve stocks, currencies, cryptocurrencies, and indices and always carries risk of loss.",
                },
                "blockchain": {
                    "es": "Blockchain es una estructura de registro distribuido en la que los datos se agrupan en bloques enlazados y se mantienen mediante una red de participantes. Se usa para registrar transacciones y otros datos de forma verificable.",
                    "pt": "Blockchain é uma estrutura de registro distribuído na qual os dados são agrupados em blocos encadeados e mantidos por uma rede de participantes. É usada para registrar transações e outros dados de forma verificável.",
                    "en": "A blockchain is a distributed ledger in which data is grouped into linked blocks and maintained by a network of participants. It can record transactions and other data in a verifiable way.",
                },
            }
            answer_set = definitions.get(subject.casefold())
            if answer_set:
                return answer_set.get(language, answer_set["es"])
        return ""

    @staticmethod
    def _specialized_evidence_answer(question: str, evidence: str, frame: dict[str, Any]) -> str:
        if not evidence: return ""
        q = question.lower()
        domain = str(frame.get("domain") or "")

        if domain == "weather" or "WEATHER SOURCE: Open-Meteo" in evidence:
            if "WEATHER SOURCE: Open-Meteo" not in evidence: return ""
            def field(name: str) -> str:
                match = re.search(rf"^{re.escape(name)}:\s*(.+)$", evidence, re.I | re.M)
                return match.group(1).strip() if match else ""
            location = field("LOCATION"); observed = field("OBSERVATION TIME"); temperature = field("TEMPERATURE")
            apparent = field("APPARENT TEMPERATURE"); humidity = field("RELATIVE HUMIDITY"); wind = field("WIND SPEED"); condition = field("CONDITION")
            if not temperature: return "Bitey IA recuperó datos meteorológicos de Open-Meteo, pero el campo de temperatura no estuvo disponible en la respuesta verificada."
            language = str(frame.get("language") or "es")
            if language == "pt":
                answer = f"Em {location or 'a localização solicitada'}, a temperatura registrada é {temperature}."
                if apparent: answer += f" Sensação térmica: {apparent}."
                if condition: answer += f" Condição: {condition}."
                if humidity: answer += f" Umidade relativa: {humidity}."
                if wind: answer += f" Vento: {wind}."
                if observed: answer += f" Observado em {observed}."
                return answer + " Fonte: Open-Meteo."
            if language == "en":
                answer = f"In {location or 'the requested location'}, the recorded temperature is {temperature}."
                if apparent: answer += f" Feels like: {apparent}."
                if condition: answer += f" Condition: {condition}."
                if humidity: answer += f" Relative humidity: {humidity}."
                if wind: answer += f" Wind: {wind}."
                if observed: answer += f" Observed at {observed}."
                return answer + " Source: Open-Meteo."
            answer = f"En {location or 'la ubicación solicitada'}, la temperatura registrada es {temperature}."
            if apparent: answer += f" Sensación térmica: {apparent}."
            if condition: answer += f" Condición: {condition}."
            if humidity: answer += f" Humedad relativa: {humidity}."
            if wind: answer += f" Viento: {wind}."
            if observed: answer += f" Observado a las {observed}."
            return answer + " Fuente: Open-Meteo."

        trading = frame.get("domain") == "trading" or bool(re.search(r"\b(?:[a-z]{2,12}(?:usdt|usd)|[a-z]{6})\b|\b(?:m1|m3|m5|m15|m30|h1|h4|d1|w1|mn1)\b", q, re.I))
        if not trading: return ""
        if "sbt_module_not_configured" in evidence or "not configured for Bitey IA Web" in evidence:
            return ("He clasificado correctamente la solicitud como análisis de trading y el flujo SBT fue seleccionado, pero SBT todavía no está conectado a una fuente de mercado verificable desde Bitey IA Web.\n\n"
                    "Por seguridad no voy a inventar el precio, RSI, tendencia, señal, entrada, stop loss ni take profit.\n\n"
                    "Estado: SBT seleccionado · datos de mercado verificados: no disponibles · ejecución real: deshabilitada.")
        if "No verified market data" in evidence or "No hay datos de mercado verificados" in evidence or "could not obtain verified market data" in evidence:
            return ("Bitey IA seleccionó SBT para analizar el mercado, pero no recibió datos de mercado verificados para esta solicitud.\n\n"
                    "No voy a inventar precio, indicadores ni una señal de entrada/salida.\n\n"
                    "Estado: Bitey IA → SBT · datos verificados: no disponibles · ejecución real: deshabilitada.")
        if "SBT verified market analysis" in evidence:
            price=re.search(r"Last price:\s*([^\.]+)",evidence,re.I); bias=re.search(r"Bias:\s*([^\.]+)",evidence,re.I); confidence=re.search(r"Confidence:\s*([^\.]+)",evidence,re.I)
            return ("Bitey IA recibió datos de mercado verificados y ejecutó el análisis técnico mediante SBT en modo research-only.\n\n"
                    f"Precio de referencia: {price.group(1).strip() if price else 'no especificado'}\nSesgo: {bias.group(1).strip() if bias else 'no especificado'}\nConfianza: {confidence.group(1).strip() if confidence else 'no especificada'}\n\n"
                    "La ejecución de órdenes permanece deshabilitada. Los datos proceden del módulo SBT verificado.")
        return ""

    @classmethod
    def _reason_from_evidence(cls, question: str, evidence: str, frame: dict[str, Any], decision: dict[str, Any]) -> str:
        claims=cls._extract_claims(evidence,question)
        if not claims:return ""
        language=cls._answer_language(question,frame.get("language")); confidence=float(frame.get("confidence") or 0.0); risk=bool(decision.get("risk_flags"))
        if language=="en": lead,limit,confidence_line="I found relevant evidence for the question.","The points below are limited to what the retrieved sources support.",f"Evidence-grounded confidence: {confidence:.0%}."; risk_line=" Verify critical details before acting." if risk else ""
        elif language=="pt": lead,limit,confidence_line="Encontrei evidências relevantes para a pergunta.","Os pontos abaixo estão limitados ao que as fontes recuperadas sustentam.",f"Confiança baseada em evidências: {confidence:.0%}."; risk_line=" Confirme detalhes críticos antes de agir." if risk else ""
        else: lead,limit,confidence_line="Encontré evidencia relevante para la pregunta.","Los puntos siguientes se limitan a lo que respaldan las fuentes recuperadas.",f"Confianza basada en evidencia: {confidence:.0%}."; risk_line=" Verifica los detalles críticos antes de actuar." if risk else ""
        source_count = len(re.findall(r"(?im)^SOURCE\\s+(\\d+)\\s*:", evidence))
        refs = [f"[S{i}]" for i in range(1, min(source_count, 3) + 1)]
        bullets = []
        for index, claim in enumerate(claims[:3]):
            marker = refs[min(index, len(refs) - 1)] if refs else ""
            bullets.append(f"- {claim} {marker}".rstrip())
        bullet_text = "\n".join(bullets)
        return f"{lead}\n\n{bullet_text}\n\n{limit}{risk_line}\n\n{confidence_line}"

    @staticmethod
    def _extract_claims(evidence: str, question: str) -> list[str]:
        stop={"qué","que","cuál","cual","cuántos","cuantos","cuántas","cuantas","cómo","como","tiene","tienen","hay","para","por","del","de","la","el","los","las","un","una","en","y","o","a","the","what","how","many","is","are","for","of","in","and"}
        q_tokens={t.lower() for t in re.findall(r"[\wÀ-ÿ]+",question) if len(t)>=3 and t.lower() not in stop}; candidates=[]; seen=set()
        for raw in re.split(r"(?<=[.!?])\s+|\n+",evidence):
            clean=re.sub(r"\s+"," ",raw).strip(" -•")
            if len(clean)<35 or re.match(r"^(?:SOURCE|TITLE|URL|SNIPPET|LINK|FUENTE|TÍTULO|EVIDENCE)\b",clean,re.I) or clean.startswith(("http://","https://")):continue
            words={t.lower() for t in re.findall(r"[\wÀ-ÿ]+",clean)}; score=float(len(q_tokens&words)*3)
            if re.search(r"\b20\d{2}\b",clean):score+=2
            if re.search(r"\b\d+(?:[.,]\d+)?\b",clean):score+=1.5
            conceptual = bool(re.match(r"^(?:[¿?]\\s*)?(?:qué|que|cuál|cual|cómo|como)\\s+(?:es|son|significa|funciona)\\b", question, re.I))
            minimum_score = 3 if conceptual else 8
            if score < minimum_score:continue
            if len(clean)>360:clean=clean[:357].rsplit(" ",1)[0]+"..."
            key=re.sub(r"\W+"," ",clean.lower()).strip()
            if key not in seen:seen.add(key);candidates.append((score,clean))
        candidates.sort(key=lambda item:(-item[0],len(item[1])));return [claim for _score,claim in candidates[:8]]

    @staticmethod
    def _answer_language(question: str, frame_language: str|None) -> str:
        tokens=set(re.findall(r"[\wÀ-ÿ]+",question.lower())); es=sum(t in {"qué","cómo","quiero","puede","necesito","los","las","del","una"} for t in tokens); pt=sum(t in {"que","como","quero","pode","preciso","os","as","dos","uma","não"} for t in tokens); en=sum(t in {"what","how","want","can","please","the"} for t in tokens)
        if es>=2 and es>pt:return "es"
        if pt>=2 and pt>es:return "pt"
        if en>=2 and en>max(es,pt):return "en"
        return frame_language or "es"

    @staticmethod
    def _contextual_guarded_answer(question: str, frame: dict[str, Any], decision: dict[str, Any], context: dict[str, Any]) -> str:
        language = str(frame.get("language") or "es")
        domain = str(frame.get("domain") or "general")
        intent = str(frame.get("intent") or "unknown")
        confidence = float(frame.get("confidence") or 0.0)
        required = bool(context.get("research_required"))
        selected_tools = context.get("selected_tools") or []
        tool_results = context.get("tool_results") or {}
        evidence_attempted = bool(context.get("evidence_attempted") or context.get("evidence_required") or context.get("evidence_source_count"))
        failure = str(context.get("research_failure") or "").strip()
        if not failure:
            failed_tools = [name for name, result in tool_results.items() if isinstance(result, dict) and result.get("ok") is False]
            if failed_tools: failure = "fallaron: " + ", ".join(failed_tools)
        if language == "pt":
            if failure:
                return f"Sou a Bitey IA. Identifiquei a solicitação como '{domain}' e tentei obter evidências, mas a fonte necessária não respondeu corretamente ({failure}). Não vou inventar o dado ausente. Posso responder quando uma fonte verificável estiver disponível."
            if required or evidence_attempted:
                return f"Sou a Bitey IA. Identifiquei a solicitação como '{domain}' e fiz a tentativa de pesquisa disponível, mas não obtive evidência verificável suficiente para uma conclusão factual. Não vou inventar o dado ausente."
            return f"Sou a Bitey IA. Entendi a solicitação como '{intent}' no domínio '{domain}', mas este pedido ainda não está conectado a uma ferramenta de dados verificável. Não vou inventar a resposta."
        if language == "en":
            if failure:
                return f"I'm Bitey IA. I classified this request as '{domain}' and tried to obtain evidence, but the required source did not respond correctly ({failure}). I won't invent the missing data. I can answer when a verifiable source is available."
            if required or evidence_attempted:
                return f"I'm Bitey IA. I classified this request as '{domain}' and attempted the available research path, but it did not produce enough verifiable evidence for a factual conclusion. I won't invent the missing data."
            return f"I'm Bitey IA. I understood the request as '{intent}' in the '{domain}' domain, but this request is not yet connected to a verifiable data tool. I won't invent the answer."
        if failure:
            return f"Soy Bitey IA. Clasifiqué la solicitud como '{domain}' e intenté obtener evidencia, pero la fuente necesaria no respondió correctamente ({failure}). No voy a inventar el dato que falta. Podré responder cuando exista una fuente verificable disponible."
        if required or evidence_attempted:
            return f"Soy Bitey IA. Clasifiqué la solicitud como '{domain}' y realicé la ruta de investigación disponible, pero no produjo evidencia verificable suficiente para una conclusión factual. No voy a inventar el dato que falta."
        return f"Soy Bitey IA. Entendí la solicitud como '{intent}' dentro del dominio '{domain}', pero esta petición todavía no está conectada a una herramienta de datos verificable. No voy a inventar la respuesta."
