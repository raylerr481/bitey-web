from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re
from difflib import SequenceMatcher


@dataclass
class CognitiveState:
    perception: dict[str, Any] = field(default_factory=dict)
    intention: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    decision: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"perception": self.perception, "intention": self.intention, "context": self.context, "plan": self.plan, "evidence": self.evidence, "confidence": self.confidence, "decision": self.decision}


class CognitiveModel:
    """Domain-neutral structured cognition used before model routing."""

    _INTENT_FAMILIES = ("knowledge", "current_info", "weather", "time", "math", "programming", "file_analysis", "local_search", "comparison", "recommendation", "translation", "summarization", "planning", "creative", "research", "conversation")
    _KNOWN_LOCATIONS = ("esteio", "porto alegre", "são leopoldo", "novo hamburgo", "canoas", "gramado", "caxias do sul", "são paulo", "rio de janeiro", "brasília", "curitiba", "florianópolis", "belo horizonte", "salvador", "lisboa", "madrid", "barcelona", "miami", "new york", "london")

    _DOMAIN_HINTS = {
        "weather": ("temperatura", "clima", "weather", "temperature", "forecast", "previsão", "previsao", "tiempo"),
        "finance": ("precio", "precios", "cotización", "cotizacion", "acción", "acciones", "stock", "dividendo", "dividendos", "finanzas"),
        "trading": ("trading", "trade", "forex", "stock", "tradingview", "mt5"),
        "support": ("ticket", "soporte", "error", "incidencia", "reparación", "repair"),
        "programming": ("código", "codigo", "python", "javascript", "api", "bug", "programar"),
        "marketing": ("marketing", "ventas", "campaña", "publicidad", "seo"),
        "research": ("investiga", "investigar", "research", "evidencia", "fuentes", "estudio"),
        "local_search": ("cerca de mí", "cerca de mi", "cercano", "cercana", "near me", "nearby", "en mi zona"),
        "translation": ("traduce", "traducir", "traducción", "traduccion", "translate"),
        "summarization": ("resume", "resumir", "resumen", "summarize", "summary"),
        "planning": ("planifica", "planificar", "itinerario", "paso a paso", "organiza", "organizar"),
        "comparison": ("compara", "comparar", "diferencia entre", "versus", " vs "),
        "recommendation": ("recomienda", "recomiéndame", "recomendación", "recomendacion", "qué me conviene", "should i"),
        "time": ("qué hora", "que hora", "hora actual", "what time", "current time"),
        "math": ("calcula", "calcular", "cuánto es", "cuanto es", "porcentaje", "ecuación", "ecuacion", "probabilidad"),
        "creative": ("escribe una historia", "poema", "poesía", "poesia", "cuento", "guion", "slogan"),
    }

    _STRONG_INTENT = {
        "research": ("investiga", "investigar", "research", "compara", "fuentes", "evidencia"),
        "trading": ("eurusd", "gbpusd", "xauusd", "btc/usd", "btcusd", "forex", "mt5", "tradingview", "estrategia de trading", "bot de trading", "bot para trading", "señal de trading", "analiza btc", "analiza eth", "analiza eurusd", "backtest", "backtesting"),
        "weather": ("qué temperatura", "que temperatura", "temperatura actual", "clima actual", "pronóstico", "pronostico", "weather", "tiempo hoy", "el tiempo hoy", "tiempo en", "qué tiempo es", "que tiempo es", "qué tiempo hace", "que tiempo hace", "clima en", "como esta el tiempo", "cómo está el tiempo", "com esta el tiempo", "com esta el clima"),
        "programming": ("escribe código", "escribe codigo", "programa", "implementa", "debug", "api rest", "crear un bot", "crea un bot", "puedes crear bot"),
        "finance": ("precio de", "precio ahora", "cotiza", "cotización", "cotizacion", "acciones de", "acción de", "dividendos", "valor de mercado"),
    }

    _GREETING_PATTERNS = (
        r"^hola[!,.¡¿?\s]*$", r"^holi[!,.¡¿?\s]*$", r"^hello[!,.¡¿?\s]*$",
        r"^hi[!,.¡¿?\s]*$", r"^hey[!,.¡¿?\s]*$", r"^buenos?\s+d[ií]as[!,.¡¿?\s]*$",
        r"^buenas\s+(tardes|noches)[!,.¡¿?\s]*$", r"^boa\s+(tarde|noite)[!,.¡¿?\s]*$",
    )

    _IDENTITY_PATTERNS = (
        r"^(?:[¿?\s]*)qu[ií]e?n\s+eres[?!.,¡¿\s]*$",
        r"^(?:[¿?\s]*)qu[eé]\s+eres[?!.,¡¿\s]*$",
        r"^(?:[¿?\s]*)qu[eé]\s+puedes\s+hacer[?!.,¡¿\s]*$",
        r"^(?:[¿?\s]*)qu[eé]\s+haces[?!.,¡¿\s]*$",
        r"^(?:[¿?\s]*)c[oó]mo\s+funcionas[?!.,¡¿\s]*$",
        r"^(?:[¿?\s]*)what\s+are\s+you[?!.,\s]*$",
        r"^(?:[¿?\s]*)who\s+are\s+you[?!.,\s]*$",
        r"^(?:[¿?\s]*)what\s+can\s+you\s+do[?!.,\s]*$",
        r"^(?:[¿?\s]*)qual\s+[eé]\s+voc[eê][?!.,\s]*$",
        r"^(?:[¿?\s]*)o\s+que\s+voc[eê]\s+faz[?!.,\s]*$",
    )

    _CONCEPTUAL_CUES = (
        "qué es", "que es", "qué son", "que son", "qué significa", "que significa",
        "cómo funciona", "como funciona", "definición", "definicion", "define",
        "explica", "explícame", "explicame", "concepto", "what is", "what are",
        "how does", "qual é", "o que é", "o que são", "como funciona",
    )

    _FOLLOWUP_WORDS = ("eso", "esto", "ello", "ese", "esa", "allí", "alli", "ahí", "ahi", "mañana", "manana", "ayer", "antes", "después", "despues", "otra", "otro", "anterior", "siguiente", "precio", "seguir", "continúa", "continua", "analízalo", "analizalo", "hazlo", "explícalo", "explicalo")
    _MARKET_INSTRUMENT_RE = re.compile(r"\b(?:[A-Z]{2,12}(?:USDT|USD)|[A-Z]{6}|XAUUSD|XAGUSD)\b", re.I)
    _MARKET_ACTION_CUES = ("precio", "cotización", "cotizacion", "valor", "cuánto vale", "cuanto vale", "cómo está", "como esta", "ahora", "ahora mismo", "cotiza")

    _ROUTING_ALIASES = {
        "hoka": "hola", "holaa": "hola", "holla": "hola", "ola": "hola", "olaa": "hola",
        "orto": "porto", "poto": "porto",
        "tienpo": "tiempo", "timepo": "tiempo", "timepoe": "tiempo", "temppo": "tiempo", "tiemp": "tiempo", "tiemp": "tiempo", "cllima": "clima", "climma": "clima", "com": "como",
        "contiua": "continua", "contina": "continua", "continuaaa": "continua",
        "preico": "precio", "prceio": "precio", "cotizacon": "cotizacion", "accin": "accion",
    }

    @classmethod
    def _routing_vocabulary(cls) -> tuple[str, ...]:
        groups = list(cls._DOMAIN_HINTS.values()) + list(cls._STRONG_INTENT.values()) + [cls._FOLLOWUP_WORDS]
        words = {"hola", "holi", "hello", "hey", "buenas", "temperatura", "tiempo", "clima", "continua", "continúa"}
        for group in groups:
            for word in group:
                if len(word) >= 4 and " " not in word:
                    words.add(word.lower())
        return tuple(words)

    @classmethod
    def _normalize_for_routing(cls, text: str) -> str:
        """Correct only high-confidence typos for intent routing."""
        # Common keyboard omission in conceptual questions. Keep this narrowly
        # scoped so the short token "qu" is not globally rewritten.
        text = re.sub(
            r"\bqu\s+(?=(?:es|son|significa|funciona)\b)",
            "qué ",
            text,
            flags=re.I,
        )
        # Recover very common short keyboard/transposition errors in conceptual
        # questions, e.g. "que e sla nasa" -> "qué es la nasa". Keep this
        # narrowly scoped to the conceptual grammar so arbitrary text is not
        # rewritten.
        text = re.sub(
            r"\b(?:que|qué)\s+e\s+sla\s+",
            "qué es la ",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"\b(?:que|qué)\s+e\s+la\s+",
            "qué es la ",
            text,
            flags=re.I,
        )
        vocabulary = cls._routing_vocabulary()
        tokens = re.findall(r"[\wÀ-ÿ]+|[^\wÀ-ÿ]+", text.strip(), re.UNICODE)
        normalized = []
        for token in tokens:
            if not re.fullmatch(r"[\wÀ-ÿ]+", token, re.UNICODE):
                normalized.append(token)
                continue
            lowered = token.lower()
            if lowered in cls._ROUTING_ALIASES:
                normalized.append(cls._ROUTING_ALIASES[lowered])
                continue
            if len(lowered) >= 4:
                best = max(vocabulary, key=lambda candidate: SequenceMatcher(None, lowered, candidate).ratio())
                ratio = SequenceMatcher(None, lowered, best).ratio()
                if ratio >= 0.88 and abs(len(lowered) - len(best)) <= 2:
                    normalized.append(best)
                    continue
            normalized.append(token)
        return "".join(normalized)

    @classmethod
    def _is_greeting(cls, text: str) -> bool:
        normalized = " ".join(text.lower().strip().split())
        return any(re.fullmatch(pattern, normalized, flags=re.I) for pattern in cls._GREETING_PATTERNS)

    @classmethod
    def _is_identity_request(cls, text: str) -> bool:
        normalized = " ".join(text.lower().strip().split())
        return any(re.fullmatch(pattern, normalized, flags=re.I) for pattern in cls._IDENTITY_PATTERNS)

    def perceive(self, message: str) -> dict[str, Any]:
        text = self._normalize_for_routing(message)
        words = len(text.split())
        return {
            "message_length": len(text),
            "word_count": words,
            "language_hint": self._language_hint(text),
            "question": "?" in text or bool(re.match(r"^(que|qué|como|cómo|por que|por qué|what|how|why|qual|onde|quando)\b", text.lower())),
            "has_url": bool(re.search(r"https?://|www\.", text, re.I)),
            "greeting": self._is_greeting(text),
            "identity_request": self._is_identity_request(text),
            "complexity_signal": min(1.0, 0.20 + min(0.30, words / 180)),
        }

    @classmethod
    def _intent_family(cls, text: str, domain: str) -> tuple[str, float]:
        low = text.casefold()
        if cls._is_greeting(low) or cls._is_identity_request(low):
            return "conversation", 0.98
        if any(x in low for x in ("traduce", "traducir", "traducción", "traduceme", "translate")):
            return "translation", 0.95
        if any(x in low for x in ("resume", "resumir", "resumen", "summarize", "summary")):
            return "summarization", 0.92
        if any(x in low for x in ("qué hora", "que hora", "hora actual", "hora en ", "what time", "current time")):
            return "time", 0.94
        if bool(re.fullmatch(r"[0-9.,\s()+*/%^=-]+", low)) or any(x in low for x in ("cuánto es", "cuanto es", "calcula", "calcular", "porcentaje", "ecuación", "ecuacion", "probabilidad")):
            return "math", 0.94
        if domain == "weather":
            return "weather", 0.98
        if domain == "programming":
            return "programming", 0.92
        if domain == "local_search":
            return "local_search", 0.90
        if domain == "research":
            return "research", 0.90
        if any(x in low for x in ("compara", "comparar", "diferencia entre", " versus ", " vs ")):
            return "comparison", 0.90
        if any(x in low for x in ("recomienda", "recomiéndame", "recomendación", "recomendacion", "qué me conviene", "que me conviene", "should i")):
            return "recommendation", 0.88
        if any(x in low for x in ("planifica", "planificar", "itinerario", "paso a paso", "organiza", "organizar")):
            return "planning", 0.88
        if any(x in low for x in ("escribe una historia", "poema", "poesía", "poesia", "cuento", "guion", "slogan")):
            return "creative", 0.90
        if domain in {"finance", "trading"} and any(x in low for x in ("ahora", "hoy", "actual", "precio", "cotiza", "cotización")):
            return "current_info", 0.88
        if any(x in low for x in ("ahora", "hoy", "actualmente", "último", "ultimo", "reciente", "latest", "current", "en vivo", "tiempo real")):
            return "current_info", 0.82
        return "knowledge", 0.62

    @classmethod
    def build_execution_policy(cls, intention: dict[str, Any], message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Translate intent into a capability plan without hard-coding every question."""
        ctx = context or {}
        family = str(intention.get("intent_family") or "knowledge")
        confidence = float(intention.get("intent_confidence") or intention.get("confidence") or 0.0)
        freshness = bool(ctx.get("freshness_required"))
        explicit_research = bool(ctx.get("requires_web_research") or ctx.get("research"))
        direct_tools = {
            "weather": ["weather"],
            "time": ["time"],
            "math": ["calculator"],
            "programming": ["code_reasoning"],
            "file_analysis": ["file_context"],
            "local_search": ["local_search"],
        }
        tool_chain = list(direct_tools.get(family, []))
        if family in {"current_info", "research"} or explicit_research or freshness:
            tool_chain.append("web_research")
        if family in {"comparison", "recommendation"}:
            tool_chain.extend(["web_research", "reasoning"])
        if family in {"knowledge", "translation", "summarization", "planning", "creative", "conversation"}:
            tool_chain.append("llm")
        if "reasoning" not in tool_chain and family not in {"conversation", "math", "time", "weather"}:
            tool_chain.append("reasoning")
        deduped = list(dict.fromkeys(tool_chain)) or ["llm"]
        return {
            "intent_family": family,
            "confidence": round(max(0.0, min(1.0, confidence)), 3),
            "capabilities": deduped,
            "requires_evidence": bool("web_research" in deduped or family in {"weather", "time", "local_search"}),
            "fallback_order": ["llm", "web_research", "reasoning"],
            "answer_strategy": "direct" if family in {"conversation", "math", "time", "translation"} else "synthesize",
        }

    @classmethod
    def _extract_entities(cls, text: str) -> dict[str, list[str]]:
        """Extract locations even from lowercase, short, typo-prone queries."""
        normalized = cls._normalize_for_routing(text).lower()
        found: list[str] = []
        for location in cls._KNOWN_LOCATIONS:
            if re.search(r"(?<![\wÀ-ÿ])" + re.escape(location) + r"(?![\wÀ-ÿ])", normalized, re.I):
                found.append(location)
        contextual = re.findall(
            r"\b(?:en|in|em|cerca de|near)\s+([A-Za-zÀ-ÿ][\wÀ-ÿ-]*(?:\s+[A-Za-zÀ-ÿ][\wÀ-ÿ-]*){0,3})",
            normalized, flags=re.UNICODE | re.I,
        )
        for location in contextual:
            cleaned = location.strip(" ,.!?").lower()
            if cleaned and cleaned not in found:
                found.append(cleaned)
        urls = re.findall(r"https?://[^\s]+|www\.[^\s]+", text, flags=re.I)
        instruments = [match.upper() for match in cls._MARKET_INSTRUMENT_RE.findall(text)]
        return {"locations": found[:8], "urls": urls[:8], "instruments": instruments[:8]}
    def infer_intention(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        text = self._normalize_for_routing(message).lower()
        scores = {domain: sum(1 for hint in hints if hint in text) for domain, hints in self._DOMAIN_HINTS.items()}
        weather_terms = ("tiempo", "clima", "temperatura", "weather")
        weather_temporal = any(x in text for x in weather_terms) and any(x in text for x in ("hoy", "ahora", "actual", "actualmente", "ahora mismo"))
        weather_location_question = bool(
            re.search(r"\b(?:tiempo|clima|temperatura|weather)\b.*\b(?:en|in|em)\b", text)
            or (
                any(term in text for term in weather_terms)
                and any(re.search(r"(?<![\wÀ-ÿ])" + re.escape(location) + r"(?![\wÀ-ÿ])", text, re.I) for location in self._KNOWN_LOCATIONS)
            )
        )
        weather_state_question = bool(re.search(r"\b(?:como|cómo)\s+(?:esta|está)\s+(?:el\s+)?(?:tiempo|clima)\b", text))
        if weather_temporal or weather_location_question or weather_state_question:
            scores["weather"] = max(scores.get("weather", 0), 2)
            strong_scores_hint = True
        else:
            strong_scores_hint = False
        finance_current = any(x in text for x in ("precio", "cotización", "cotizacion", "cotiza", "acciones", "dividendos")) and any(x in text for x in ("ahora", "hoy", "actual", "actualmente", "último", "última", "cuánto", "cuanto", "vale"))
        if finance_current:
            scores["finance"] = max(scores.get("finance", 0), 2)
        conceptual = any(cue in text for cue in self._CONCEPTUAL_CUES)
        greeting = self._is_greeting(text)
        identity_request = self._is_identity_request(text)
        strong_scores = {domain: sum(1 for hint in hints if hint in text) for domain, hints in self._STRONG_INTENT.items()}
        if strong_scores_hint:
            strong_scores["weather"] = max(strong_scores.get("weather", 0), 2)
        market_instrument = bool(self._MARKET_INSTRUMENT_RE.search(message))
        market_action = any(cue in text for cue in self._MARKET_ACTION_CUES)
        if market_instrument and market_action:
            strong_scores["trading"] = strong_scores.get("trading", 0) + 2

        if greeting:
            return {"domain": "general", "intent": "greeting", "intent_family": "conversation", "entities": self._extract_entities(message), "scores": {**scores, "general": 1}, "confidence": 0.98, "source": "structured_greeting_intent", "response_guidance": "acknowledge_the_user_greeting_naturally_and_continue_the_conversation"}

        if identity_request:
            return {"domain": "general", "intent": "self_identity", "intent_family": "conversation", "entities": self._extract_entities(message), "scores": {**scores, "general": 2}, "confidence": 0.98, "source": "structured_self_identity_intent", "response_guidance": "describe_bitey_identity_capabilities_and_scope_without_external_research"}

        if conceptual:
            current_conceptual_weather = any(x in text for x in ("actual", "ahora", "hoy", "pronóstico", "pronostico", "forecast"))
            if not current_conceptual_weather:
                scores = {domain: 0 for domain in scores}
                scores["general"] = 1
            for domain in strong_scores:
                if domain != "weather" or not current_conceptual_weather:
                    strong_scores[domain] = 0

        max_strong = max(strong_scores.values(), default=0)
        if max_strong:
            strong_domains = [d for d, score in strong_scores.items() if score == max_strong]
            if len(strong_domains) == 1:
                scores[strong_domains[0]] += 2

        # Follow-up turns inherit only the relevant semantic signal from the previous user request.
        prior_request = str(context.get("last_user_request") or "").strip()
        prior_answer = str(context.get("last_assistant_answer") or "").strip()
        is_followup = any(token in text for token in self._FOLLOWUP_WORDS)
        prior_normalized = self._normalize_for_routing(prior_request).lower() if is_followup and prior_request else ""
        if is_followup and prior_normalized:
            prior_scores = {domain: sum(1 for hint in hints if hint in prior_normalized) for domain, hints in self._DOMAIN_HINTS.items()}
            # A reference such as "the other option" may carry little lexical
            # signal itself, so use the immediately previous answer as a
            # bounded semantic bridge. It is continuity context, never evidence.
            reference_followup = bool(prior_answer) and any(
                token in text for token in ("otra", "otro", "anterior", "siguiente", "esa", "ese", "eso")
            )
            if reference_followup:
                prior_answer_normalized = self._normalize_for_routing(prior_answer).lower()
                answer_scores = {
                    domain: sum(1 for hint in hints if hint in prior_answer_normalized)
                    for domain, hints in self._DOMAIN_HINTS.items()
                }
                for domain, score in answer_scores.items():
                    if score:
                        prior_scores[domain] = max(prior_scores.get(domain, 0), min(2, score))
            prior_top = max(prior_scores.values(), default=0)
            if max(scores.values(), default=0) == 0 or prior_top >= 2:
                for domain, score in prior_scores.items():
                    if score:
                        scores[domain] = max(scores.get(domain, 0), min(2, score))
            if any(term in prior_normalized for term in weather_terms):
                scores["weather"] = max(scores.get("weather", 0), 2)
        explicit_domain = str(context.get("domain") or "").strip().lower()
        current_signal = max(scores.values(), default=0)
        if explicit_domain in scores and current_signal == 0 and is_followup:
            scores[explicit_domain] += 1

        order = ["general"] + list(self._DOMAIN_HINTS)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], order.index(item[0]) if item[0] in order else len(order)))
        top_domain, top_score = ranked[0] if ranked else ("general", 0)
        second_score = ranked[1][1] if len(ranked) > 1 else 0
        if top_score == 0:
            top_domain = "general"
        confidence = 0.55 if top_score else 0.35
        if top_score > second_score:
            confidence += min(0.25, (top_score - second_score) * 0.08)
        family, family_confidence = self._intent_family(message, top_domain)
        entities = self._extract_entities(message)
        if is_followup and prior_request:
            prior_entities = self._extract_entities(prior_request)
            if not entities.get("locations") and prior_entities.get("locations"):
                entities["locations"] = prior_entities["locations"][:8]
            if not entities.get("urls") and prior_entities.get("urls"):
                entities["urls"] = prior_entities["urls"][:8]
            if prior_answer and any(token in text for token in ("otra", "otro", "anterior", "siguiente", "esa", "ese", "eso")):
                option_refs = re.findall(r"(?:^|\n)\s*(?:\[?\d+\]?|[-•])\s+([^\n]{3,180})", prior_answer)
                stored = context.get("previous_result_context") or {}
                stored_options = stored.get("options") if isinstance(stored, dict) else []
                stored_sources = stored.get("sources") if isinstance(stored, dict) else []
                if option_refs:
                    entities["prior_options"] = [item.strip() for item in option_refs[:8]]
                elif isinstance(stored_options, list) and stored_options:
                    entities["prior_options"] = [str(item).strip()[:180] for item in stored_options[:8] if str(item).strip()]
                if isinstance(stored_sources, list) and stored_sources:
                    entities["prior_results"] = [
                        {
                            "index": item.get("index"),
                            "title": str(item.get("title") or "")[:180],
                            "url": str(item.get("url") or "")[:500],
                        }
                        for item in stored_sources[:8]
                        if isinstance(item, dict) and (item.get("title") or item.get("url"))
                    ]
            if not entities.get("instruments") and prior_entities.get("instruments"):
                entities["instruments"] = prior_entities["instruments"][:8]
            reference_map = {
                "allí": "location", "alli": "location", "ahí": "location", "ahi": "location",
                "ese": "prior_entity", "esa": "prior_entity", "eso": "prior_entity",
                "anterior": "prior_result", "siguiente": "prior_result",
                "arriba": "prior_result", "abajo": "prior_result",
                "primera": "ordinal_result", "primero": "ordinal_result",
                "segunda": "ordinal_result", "segundo": "ordinal_result",
                "tercera": "ordinal_result", "tercero": "ordinal_result",
                "cuarta": "ordinal_result", "cuarto": "ordinal_result",
            }
            references = [kind for token, kind in reference_map.items() if re.search(r"(?<![\wÀ-ÿ])" + re.escape(token) + r"(?![\wÀ-ÿ])", text, re.I)]
            if references:
                entities["references"] = list(dict.fromkeys(references))[:6]

            ordinal_map = {
                "primera": 1, "primero": 1, "segunda": 2, "segundo": 2,
                "tercera": 3, "tercero": 3, "cuarta": 4, "cuarto": 4,
            }
            ordinal_match = next(
                (number for token, number in ordinal_map.items()
                 if re.search(r"(?<![\wÀ-ÿ])" + re.escape(token) + r"(?![\wÀ-ÿ])", text, re.I)),
                None,
            )
            if ordinal_match is None:
                digit_match = re.search(r"\b(?:opción|opcion|fuente|resultado|número|numero)\s*(?:n[°º.]?\s*)?(\d+)\b", text, re.I)
                ordinal_match = int(digit_match.group(1)) if digit_match else None
            if ordinal_match is not None:
                stored = context.get("previous_result_context") or {}
                prior_results = stored.get("sources") if isinstance(stored, dict) else []
                prior_options = stored.get("options") if isinstance(stored, dict) else []
                selected = None
                if isinstance(prior_options, list) and ordinal_match <= len(prior_options):
                    selected = {"type": "option", "index": ordinal_match, "text": str(prior_options[ordinal_match - 1])[:180]}
                elif isinstance(prior_results, list) and ordinal_match <= len(prior_results):
                    item = prior_results[ordinal_match - 1]
                    if isinstance(item, dict):
                        selected = {
                            "type": "source",
                            "index": ordinal_match,
                            "title": str(item.get("title") or "")[:180],
                            "url": str(item.get("url") or "")[:500],
                        }
                if selected:
                    entities["selected_prior_result"] = selected
        return {"domain": top_domain, "intent": "answer_or_assist", "intent_family": family, "intent_confidence": family_confidence, "entities": entities, "scores": scores, "confidence": min(1.0, max(confidence, family_confidence * 0.75)), "source": "structured_intent_inference"}

    @classmethod
    def _ambiguity_profile(cls, text: str, intention: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Estimate whether the request is underspecified before choosing tools."""
        low = text.casefold()
        entities = intention.get("entities") if isinstance(intention.get("entities"), dict) else {}
        signals = []
        score = 0.0

        reference_words = ("eso", "esto", "ello", "esa", "ese", "aquello", "allí", "alli", "ahí", "ahi",
                           "la otra", "el otro", "anterior", "siguiente", "lo mismo", "eso último", "esa opción")
        if any(token in low for token in reference_words) and not context.get("last_user_request"):
            score += 0.38
            signals.append("unresolved_reference")

        comparative = any(token in low for token in (
            "mejor", "peor", "más barato", "mas barato", "más rápido", "mas rapido",
            "conviene", "alternativa", "opción", "opcion", "compara", "versus", "vs"
        ))
        if comparative and len(entities.get("prior_options", [])) < 2 and len(entities.get("prior_results", [])) < 2:
            score += 0.18
            signals.append("comparison_target_may_be_missing")

        vague_request = any(token in low for token in (
            "ayúdame", "ayudame", "hazlo", "revísalo", "revisalo", "analízalo", "analizalo",
            "me puedes ayudar", "puedes hacerlo", "qué hago", "que hago"
        ))
        if vague_request and len(low.split()) <= 8 and not entities.get("urls") and not entities.get("locations"):
            score += 0.22
            signals.append("underspecified_action")

        if intention.get("intent_family") == "knowledge" and len(low.split()) <= 3 and not any(
            cue in low for cue in cls._CONCEPTUAL_CUES
        ):
            score += 0.10
            signals.append("low_context")

        return {
            "score": round(min(1.0, score), 3),
            "signals": signals,
            "requires_clarification": score >= 0.55,
        }

    @classmethod
    def _capability_profile(cls, text: str, intention: dict[str, Any], *,
                            evidence: bool, freshness: bool, reasoning: bool) -> dict[str, Any]:
        """Map the semantic task to capabilities, independently of provider/model names."""
        low = text.casefold()
        family = str(intention.get("intent_family") or "knowledge")
        capabilities = []

        if freshness:
            capabilities.append("fresh_data")
        if evidence:
            capabilities.append("evidence_retrieval")
        if family == "weather":
            capabilities.append("weather")
        elif family == "time":
            capabilities.append("time")
        elif family == "local_search":
            capabilities.append("local_search")
        elif family == "math" or bool(re.search(r"\d\s*[+\-*/%^=]\s*\d", low)):
            capabilities.append("calculator")
        elif family == "programming":
            capabilities.append("code_reasoning")
        elif family == "file_analysis":
            capabilities.append("file_context")

        # Explicit URLs are a first-class retrieval capability, distinct from
        # generic search. This lets the brain decide to inspect the supplied
        # page rather than searching the web for it.
        if intention.get("entities", {}).get("urls"):
            capabilities.append("url_fetch")

        if family in {"comparison", "recommendation"}:
            capabilities.extend(["comparison_analysis", "decision_support"])
        if family in {"research", "current_info"} or evidence:
            capabilities.append("source_synthesis")
        if reasoning:
            capabilities.append("reasoning")
        capabilities.append("response_synthesis")

        return {"required": list(dict.fromkeys(capabilities)), "primary": capabilities[0] if capabilities else "response_synthesis"}

    def build_plan(self, message: str, context: dict[str, Any], intention: dict[str, Any]) -> dict[str, Any]:
        domain = intention.get("domain", "general")
        intent = intention.get("intent", "answer_or_assist")
        family = str(intention.get("intent_family") or "knowledge")
        if intent in {"greeting", "self_identity"}:
            return {
                "objective": "acknowledge_greeting_and_continue_conversation" if intent == "greeting" else "answer_bitey_identity_and_capabilities",
                "domain": "general",
                "intent": intent,
                "needs_evidence": False,
                "freshness_required": False,
                "requires_specialized_module": False,
                "verification_required": False,
                "stop_condition": "natural_conversational_response",
            }

        # Normalize once before any temporal or multi-step routing checks.
        lower_message = self._normalize_for_routing(message).lower()
        current_cues = (
            "ahora", "ahora mismo", "hoy", "actual", "actualmente",
            "último", "última", "ultimo", "ultima", "reciente", "latest",
            "current", "recent", "en vivo", "tiempo real", "cotiza"
        )
        explicit_current = any(cue in lower_message for cue in current_cues)
        weather_location_request = domain == "weather" and bool(re.search(r"\b(?:tiempo|clima|temperatura|weather)\b.*\b(?:en|in|em)\b", lower_message))
        weather_state_request = domain == "weather" and bool(re.search(r"\b(?:como|cómo)\s+(?:esta|está)\s+(?:el\s+)?(?:tiempo|clima)\b", lower_message))
        freshness = (
            bool(context.get("freshness_required"))
            or (domain == "weather" and (explicit_current or weather_location_request or weather_state_request))
            or (domain == "finance" and explicit_current)
        )
        evidence = freshness or bool(
            context.get("research")
            or context.get("requires_web_research")
            or context.get("needs_web")
        ) or domain == "research" or family in {"current_info", "local_search", "comparison", "recommendation"}

        step_cues = (" y luego ", " después ", " despues ", " luego ", " después de ", " despues de ", "then ", "after that", "and then", "primero", "first")
        compound = any(cue in lower_message for cue in step_cues)
        action_cues = ("analiza", "analizar", "busca", "buscar", "investiga", "calcula", "calcular", "compara", "explica", "resume", "responde", "verifica", "revisa", "implementa")
        action_count = sum(1 for cue in action_cues if cue in lower_message)
        multi_step = compound or action_count >= 2
        steps = []
        if multi_step:
            if any(cue in lower_message for cue in ("busca", "buscar", "investiga", "investigar", "fuentes")): steps.append("retrieve_evidence")
            if any(cue in lower_message for cue in ("calcula", "calcular", "porcentaje", "cuánto", "cuanto")): steps.append("calculate")
            if any(cue in lower_message for cue in ("analiza", "analizar", "revisa", "revisar", "compara")): steps.append("analyze")
            if any(cue in lower_message for cue in ("verifica", "verificar", "contrasta", "contrastar")): steps.append("verify")
            steps.append("synthesize_answer")

        # Cognitive planning is a decision layer, not a keyword-to-tool lookup.
        # It separates objective, evidence, reasoning depth, and capabilities.
        entities = intention.get("entities", {}) if isinstance(intention.get("entities"), dict) else {}
        has_reference = bool(entities.get("references") or entities.get("selected_prior_result") or entities.get("prior_results"))
        ambiguity = float(context.get("ambiguity", 0.0) or 0.0)
        confidence = float(intention.get("intent_confidence") or intention.get("confidence") or 0.0)
        conceptual = any(cue in lower_message for cue in self._CONCEPTUAL_CUES)
        comparison_task = family in {"comparison", "recommendation"} or any(
            cue in lower_message for cue in ("compara", "comparar", "mejor", "mejor opción", "mejor opcion", "alternativa", "pros y contras", "ventajas y desventajas")
        )
        calculation_task = family == "math" or bool(re.search(r"\d\s*[+\-*/%^=]\s*\d", lower_message))
        programming_task = family == "programming" or any(
            cue in lower_message for cue in ("código", "codigo", "debug", "error", "exception", "api", "endpoint", "backend", "frontend")
        )
        ambiguity_profile = self._ambiguity_profile(lower_message, intention, context)
        ambiguity = max(ambiguity, float(ambiguity_profile.get("score", 0.0)))

        reasoning_required = bool(
            multi_step or comparison_task or programming_task
            or family in {"research", "planning", "recommendation"}
            or any(cue in lower_message for cue in (
                "por qué", "porque", "cómo funciona", "como funciona", "explica por qué",
                "analiza", "evalúa", "evalua", "estima", "calcula", "estrategia",
                "qué debería", "que deberia", "should", "why", "how does"
            ))
            or (not conceptual and confidence < 0.70)
            or ambiguity >= 0.35
        )

        # Current/factual questions need evidence even when the router cannot
        # confidently name a specialized domain.
        generic_factual_signal = bool(re.search(
            r"\b(?:quién|quien|dónde|donde|cuándo|cuando|cuál|cual|cuánto|cuanto|precio|valor|qué pasó|que paso|qué ocurrió|que ocurrio)\b",
            lower_message,
        ))
        if generic_factual_signal and not conceptual and family not in {"conversation", "creative", "translation", "summarization"}:
            evidence = True

        if comparison_task:
            evidence = True
            if "retrieve_evidence" not in steps:
                steps.insert(0, "retrieve_evidence")
            if "analyze" not in steps:
                steps.append("analyze")
        if reasoning_required and "analyze" not in steps and family not in {"conversation", "translation"}:
            steps.append("analyze")
        if evidence and "retrieve_evidence" not in steps:
            steps.insert(0, "retrieve_evidence")
        if evidence and "verify" not in steps:
            steps.append("verify")
        if not steps and not conceptual and family not in {"conversation", "creative"}:
            steps.append("reason_about_request")

        capability_profile = self._capability_profile(
            lower_message,
            intention,
            evidence=evidence,
            freshness=freshness,
            reasoning=reasoning_required,
        )

        tool_strategy: list[str] = []
        if freshness:
            tool_strategy.append("fresh_data")
        if evidence:
            tool_strategy.append("web_research")
        if calculation_task:
            tool_strategy.append("calculator")
        if programming_task:
            tool_strategy.append("code_reasoning")
        if family == "weather":
            tool_strategy.insert(0, "weather")
        elif family == "time":
            tool_strategy.insert(0, "time")
        elif family == "local_search":
            tool_strategy.insert(0, "local_search")
        elif family == "file_analysis":
            tool_strategy.insert(0, "file_context")
        if reasoning_required:
            tool_strategy.append("reasoning")
        if ambiguity_profile.get("requires_clarification"):
            tool_strategy = ["clarify"]
        if not tool_strategy and family not in {"conversation", "creative", "translation", "summarization"}:
            tool_strategy.append("llm_synthesis")

        return {
            "objective": "retrieve_current_data_and_answer" if freshness else ("research_compare_recommend" if comparison_task else "answer_or_assist"),
            "domain": domain,
            "intent_family": family,
            "entities": entities,
            "needs_evidence": evidence,
            "freshness_required": freshness,
            "reasoning_required": reasoning_required,
            "ambiguity": round(max(0.0, min(1.0, ambiguity)), 3),
            "ambiguity_profile": ambiguity_profile,
            "intent_confidence": round(max(0.0, min(1.0, confidence)), 3),
            "has_reference_context": has_reference,
            "capabilities": capability_profile["required"],
            "primary_capability": capability_profile["primary"],
            "tool_strategy": list(dict.fromkeys(tool_strategy)),
            "requires_specialized_module": domain not in {"general", "research", "weather", "local_search", "translation", "summarization", "comparison", "recommendation", "planning", "creative", "time", "math"},
            "verification_required": evidence or domain == "research" or multi_step or reasoning_required,
            "replan_if_insufficient": bool(evidence or reasoning_required or ambiguity >= 0.35),
            "clarification_allowed": bool(ambiguity_profile.get("requires_clarification")),
            "multi_step": multi_step,
            "steps": list(dict.fromkeys(steps)),
            "stop_condition": (
                "clarification_needed_before_execution"
                if ambiguity_profile.get("requires_clarification")
                else "all_planned_steps_completed_and_verified"
                if multi_step or reasoning_required
                else "fresh_source_retrieved_and_validated"
                if freshness
                else "sufficient_confidence"
            ),
        }

    def evaluate(self, state: CognitiveState, *, evidence_available: bool = False) -> CognitiveState:
        base = float(state.intention.get("confidence", 0.35))
        if state.plan.get("needs_evidence"):
            base += 0.15 if evidence_available else -0.05
        if state.plan.get("reasoning_required"):
            base += 0.05 if state.plan.get("steps") else -0.05
        state.evidence = {
            "available": evidence_available,
            "required": bool(state.plan.get("needs_evidence")),
            "freshness_required": bool(state.plan.get("freshness_required")),
        }
        state.confidence = max(0.0, min(1.0, base))
        state.decision = {
            "mode": (
                "retrieve_reason_verify_synthesize" if state.plan.get("needs_evidence") and state.plan.get("reasoning_required")
                else "retrieve_then_respond" if state.plan.get("needs_evidence")
                else "reason_then_respond" if state.plan.get("reasoning_required")
                else "respond"
            ),
            "domain": state.intention.get("domain", "general"),
            "intent": state.intention.get("intent", "answer_or_assist"),
            "intent_family": state.intention.get("intent_family", "knowledge"),
            "entities": state.intention.get("entities", {}),
            "confidence": state.confidence,
            "evidence_required": bool(state.plan.get("needs_evidence")),
            "freshness_required": bool(state.plan.get("freshness_required")),
            "reasoning_required": bool(state.plan.get("reasoning_required")),
            "tool_strategy": list(state.plan.get("tool_strategy") or []),
            "replan_if_insufficient": bool(state.plan.get("replan_if_insufficient")),
        }
        return state

    def process(self, message: str, context: dict[str, Any] | None = None, *, evidence_available: bool = False) -> CognitiveState:
        ctx = context or {}
        cached = ctx.get("_cognitive_state")
        if isinstance(cached, CognitiveState):
            cached_message = str(cached.context.get("_cognitive_message") or "").strip()
            cached_available = bool(cached.evidence.get("available", False))
            if cached_message == message.strip():
                if cached_available != bool(evidence_available):
                    return self.evaluate(cached, evidence_available=evidence_available)
                return cached
        perception = self.perceive(message)
        intention = self.infer_intention(message, ctx)
        plan = self.build_plan(message, ctx, intention)
        state = CognitiveState(perception=perception, intention=intention, context=ctx, plan=plan)
        state.context["_cognitive_message"] = message.strip()
        return self.evaluate(state, evidence_available=evidence_available)

    @staticmethod
    def _language_hint(text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ("cómo", "qué", "quiero", "puede", "tiempo", "clima")): return "es"
        if any(token in lowered for token in ("como", "quero", "pode", "previsao", "clima")): return "pt"
        if any(token in lowered for token in ("what ", "how ", "want ", "can ", "please", "weather")): return "en"
        return "unknown"
