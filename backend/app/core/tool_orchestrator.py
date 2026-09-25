from __future__ import annotations

from ast import Expression, Constant, BinOp, UnaryOp, Add, Sub, Mult, Div, Pow, Mod, USub, UAdd, parse
from dataclasses import dataclass
import os
import re
from typing import Any, Awaitable, Callable

import httpx

from .search_gateway import search as general_search
from .cognitive_model import CognitiveModel
from .bitey_brain import BiteyBrain


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    capabilities: tuple[str, ...]
    handler: Callable[..., Awaitable[dict[str, Any]]]


class ToolOrchestrator:
    """Capability executor whose selection follows Bitey's cognitive plan."""

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)
    WEATHER_RE = re.compile(r"\b(temperatur\w*|clima|tiempo|weather|temperature|forecast|previs[aã]o)\b", re.I)
    SEARCH_RE = re.compile(r"\b(busca|buscar|búsqueda|investiga|investigar|fuentes|compara|contrasta|search|research|latest|actual|hoy|noticias|news)\b", re.I)
    FRESH_RE = re.compile(r"\b(ahora|ahora mismo|actualmente|actual|hoy|esta semana|este mes|últim[oa]s?|reciente|recientemente|en vivo|tiempo real|live|today|latest|current|recent|this week|this month)\b", re.I)
    WEB_FACT_RE = re.compile(r"\b(precio|precios|cotizaci[oó]n|disponibilidad|horario|direcci[oó]n|versi[oó]n|release|documentaci[oó]n|ley|leyes|regulaci[oó]n|reglamento|elecciones|resultados|ranking|clasificaci[oó]n|estad[ií]sticas|noticias|fuente|fuentes|comparar|compara|contrasta|rese[nñ]a|reviews?|who is|what is|how much|where|when|who|what|which)\b", re.I)
    TRADING_RE = re.compile(r"\b(?:[A-Z]{2,12}(?:USDT|USD)|[A-Z]{6}|XAUUSD|XAGUSD)\b|\b(?:M1|M3|M5|M15|M30|H1|H4|D1|W1|MN1)\b", re.I)
    MATH_RE = re.compile(r"^\s*(?:\(?\s*[-+]?\d+(?:\.\d+)?\s*\)?\s*(?:[+\-*/%^]\s*\(?\s*[-+]?\d+(?:\.\d+)?\s*\)?\s*)+)$")
    NATURAL_MATH_RE = re.compile(r"^\s*(?:cu[aá]nto\s+es\s+)?[-+]?\d+(?:[.,]\d+)?\s*(?:%\s+de|por ciento de|\+|menos|m[aá]s|por|entre|dividido(?:\s+por)?|multiplicado(?:\s+por)?|x)\s+[-+]?\d+(?:[.,]\d+)?\s*\??\s*$", re.I)

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._cognition = CognitiveModel()
        self._brain = BiteyBrain()
        self.register(ToolSpec("web_research", "Buscador web general de Bitey mediante DuckDuckGo y recuperación segura de evidencia.", ("web", "search", "research", "evidence"), self._search))
        self.register(ToolSpec("search", "Compatibility alias for Bitey web research.", ("web", "search", "research", "evidence"), self._search))
        self.register(ToolSpec("weather", "Consulta meteorología actual mediante Open-Meteo, como fuente especializada del buscador.", ("weather", "current", "forecast"), self._weather))
        self.register(ToolSpec("sbt_market", "Consulta el mercado SBT y ejecuta inteligencia técnica únicamente con datos verificables; no ejecuta órdenes.", ("trading", "market_intelligence", "market_data", "risk"), self._sbt_market))
        self.register(ToolSpec("calculator", "Calculadora local determinista para expresiones aritméticas simples; no requiere proveedor externo.", ("math", "calculation"), self._calculator))

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def available(self) -> list[dict[str, Any]]:
        return [{"name": s.name, "description": s.description, "capabilities": list(s.capabilities)} for s in self._tools.values()]

    def cognitive_selection(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {})
        cognitive = self._cognition.process(message, ctx, evidence_available=bool(ctx.get("evidence_available")))
        ctx["cognition"] = cognitive.as_dict()
        ctx["_cognitive_state"] = cognitive
        brain = self._brain.think(message, ctx)
        ctx["bitey_brain"] = brain.as_dict()
        ctx["_bitey_brain_state"] = brain
        requested = list(brain.tool_priority)
        normalized = message.casefold().strip()

        if self.MATH_RE.fullmatch(message.strip()) or self.NATURAL_MATH_RE.fullmatch(message.strip()):
            requested = ["calculator"]
        elif self.WEATHER_RE.search(message) and (
            str(cognitive.intention.get("domain", "general")).lower() == "weather"
            or "weather" in requested
        ):
            requested = ["weather"]
            if re.search(r"\b(fuente|fuentes|compara|contrasta|corrobora)\b", normalized):
                requested.append("search")
        elif brain.evidence_required and "search" not in requested:
            requested.append("search")

        requested = ["web_research" if name == "search" else name for name in requested]
        selected = [name for name in dict.fromkeys(requested) if name in self._tools]
        if context is not None:
            context.update({
                "cognition": cognitive.as_dict(),
                "_cognitive_state": cognitive,
                "bitey_brain": brain.as_dict(),
                "_bitey_brain_state": brain,
                "selected_tools": selected,
            })
        return {"cognition": cognitive.as_dict(), "brain": brain.as_dict(), "selected_tools": selected}

    @classmethod
    def needs_web_research(cls, message: str, context: dict[str, Any] | None = None) -> bool:
        ctx = context or {}
        if cls.MATH_RE.fullmatch(message.strip()):
            return False
        if bool(ctx.get("requires_web_research") or ctx.get("needs_web") or ctx.get("freshness_required")):
            return True
        return bool(cls.URL_RE.search(message) or cls.SEARCH_RE.search(message) or cls.FRESH_RE.search(message) or cls.WEB_FACT_RE.search(message))

    def select(self, message: str, context: dict[str, Any] | None = None) -> list[str]:
        return self.cognitive_selection(message, context)["selected_tools"]

    async def execute(self, names: list[str], **kwargs: Any) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for name in names:
            tool = self._tools.get(name)
            if not tool:
                continue
            try:
                results[name] = await tool.handler(**kwargs)
            except Exception as exc:
                results[name] = {"ok": False, "error": type(exc).__name__}

            if name == "weather" and not results[name].get("ok") and "web_research" in self._tools:
                try:
                    fallback = await self._tools["web_research"].handler(**kwargs)
                    if isinstance(fallback, dict):
                        fallback = dict(fallback)
                        fallback["fallback_from"] = "weather"
                        fallback["specialized_tool_error"] = results[name].get("error") or results[name].get("reason")
                    results["web_research"] = fallback
                except Exception as fallback_exc:
                    results["web_research"] = {"ok": False, "error": type(fallback_exc).__name__, "fallback_from": "weather", "specialized_tool_error": results[name].get("error") or results[name].get("reason")}

        # Preserve each tool's full result, especially web-research provenance,
        # conflict metadata, verified-source counts, and raw discovery results.
        # Older code rebuilt a synthetic "web_research" result here and silently
        # discarded those fields, which caused the main research loop to lose
        # source-count and conflict information.
        if "web_research" not in results and "search" in results:
            results["web_research"] = results["search"]

        return results

    async def _calculator(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            expression = normalize_natural_math(message)
            value = safe_calculate(expression)
            rendered = str(int(value)) if float(value).is_integer() else str(value)
            return {"ok": True, "value": value, "expression": message.strip(), "source": "local-calculator", "evidence": f"Local deterministic calculation: {message.strip()} = {rendered}"}
        except Exception as exc:
            return {"ok": False, "error": type(exc).__name__, "source": "local-calculator"}

    async def _sbt_market(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        base_url = os.getenv("SBT_MODULE_URL", "").strip().rstrip("/")
        if not base_url:
            return {"ok": False, "available": False, "verified": False, "execution_enabled": False, "reason": "sbt_module_not_configured", "evidence": "SBT market data is not configured for Bitey IA Web. No verified market data was available; no price, indicator, signal, entry, stop or take-profit was inferred."}
        instrument_match = re.search(r"\b(?:[A-Z]{2,12}(?:USDT|USD)|[A-Z]{6}|XAUUSD|XAGUSD)\b", message, re.I)
        timeframe_match = re.search(r"\b(?:M1|M3|M5|M15|M30|H1|H4|D1|W1|MN1)\b", message, re.I)
        symbol = instrument_match.group(0).upper() if instrument_match else ""
        timeframe = timeframe_match.group(0).upper() if timeframe_match else "M5"
        if not symbol:
            return {"ok": False, "available": False, "verified": False, "execution_enabled": False, "reason": "market_instrument_not_identified", "evidence": "SBT was selected for trading analysis, but the market instrument could not be identified. No market conclusion was generated."}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{base_url}/api/v1/market/candles/{symbol}", params={"timeframe": timeframe, "limit": 100})
                if response.status_code >= 400:
                    return {"ok": False, "available": False, "verified": False, "execution_enabled": False, "reason": "market_data_unavailable", "status_code": response.status_code, "evidence": f"SBT could not provide verified {symbol} {timeframe} market data. No price or signal was inferred."}
                payload = response.json()
                candles = payload.get("candles") or []
                source = payload.get("source") or "unknown"
                if len(candles) < 35:
                    return {"ok": False, "available": False, "verified": False, "execution_enabled": False, "reason": "insufficient_market_data", "symbol": symbol, "timeframe": timeframe, "candle_count": len(candles), "source": source, "evidence": f"SBT returned only {len(candles)} verified candles for {symbol} {timeframe}; at least 35 are required for baseline analysis. No signal was generated."}
                analysis = await client.post(f"{base_url}/api/v1/sbt/market-intelligence/analyze", json={"symbol": symbol, "timeframe": timeframe, "candles": candles, "language": "es", "event": "market_structure"})
                if analysis.status_code >= 400:
                    return {"ok": False, "available": True, "verified": True, "execution_enabled": False, "reason": "sbt_analysis_unavailable", "symbol": symbol, "timeframe": timeframe, "source": source, "evidence": "Verified market data was received from SBT, but SBT analysis failed. No trading signal was generated."}
                result = analysis.json()
        except (httpx.HTTPError, ValueError) as exc:
            return {"ok": False, "available": False, "verified": False, "execution_enabled": False, "reason": "sbt_connection_error", "error": type(exc).__name__, "evidence": f"Bitey could not obtain verified market data from SBT for {symbol} {timeframe}. No market conclusion was generated."}
        result["execution_enabled"] = False
        result["verified_market_data"] = True
        result["source"] = source
        result["evidence"] = f"SBT verified market analysis for {symbol} {timeframe}. Source: {source}. Candles: {len(candles)}. Last price: {result.get('last_price')}. Bias: {result.get('bias')}. Confidence: {result.get('confidence')}. SBT remains research-only and execution is disabled."
        return {"ok": True, "available": True, "verified": True, "execution_enabled": False, "symbol": symbol, "timeframe": timeframe, "source": source, "analysis": result, "evidence": result["evidence"]}

    async def _search(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        import asyncio
        from urllib.parse import urlparse
        from .search_gateway import safe_fetch

        result = await asyncio.to_thread(general_search, message, 8)
        raw_results = result.get("results") or []
        enriched: list[dict[str, Any]] = []

        def quality(url: str) -> tuple[float, str]:
            host = (urlparse(url).hostname or "").lower()
            if host.endswith(".gov") or ".gov." in host:
                return 1.0, "government"
            if host.endswith(".edu") or ".edu." in host:
                return 0.95, "academic"
            if any(host == d or host.endswith("." + d) for d in ("who.int", "wikipedia.org")):
                return 0.85, "reference"
            if host:
                return 0.65, "web_source"
            return 0.0, "unknown"

        async def enrich(item: dict[str, Any]) -> dict[str, Any]:
            url = str(item.get("url") or "")
            score, category = quality(url)
            page = await asyncio.to_thread(safe_fetch, url, 80000) if url else {"ok": False}
            out = dict(item)
            out["source_quality"] = score
            out["source_category"] = category
            if page.get("ok"):
                out["page_evidence"] = str(page.get("content") or "")[:5000]
                out["evidence_verified"] = True
            else:
                out["evidence_verified"] = False
            return out

        for item in await asyncio.gather(*(enrich(item) for item in raw_results[:6])):
            enriched.append(item)

        enriched.sort(key=lambda item: (bool(item.get("evidence_verified")), float(item.get("source_quality", 0.0))), reverse=True)
        result["results"] = enriched
        verified = [item for item in enriched if item.get("evidence_verified") and item.get("page_evidence")]
        evidence_blocks = []
        for i, item in enumerate(verified[:6], 1):
            evidence_blocks.append(
                f"SOURCE {i}: {item.get('url')}\n"
                f"TITLE: {item.get('title', '')}\n"
                f"SOURCE QUALITY: {item.get('source_quality', 0.0):.2f} ({item.get('source_category', 'unknown')})\n"
                f"EVIDENCE VERIFIED: true\n"
                f"CONTENT: {str(item.get('page_evidence'))[:5000]}"
            )
        evidence = "\n\n".join(evidence_blocks)

        def conflict_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            """Find conservative cross-source numeric/date and polarity disagreements."""
            records: list[dict[str, Any]] = []
            negation = re.compile(r"\b(?:no|not|never|without|did not|does not|cannot|can't|isn't|aren't|wasn't|weren't)\b", re.I)
            sentence_re = re.compile(r"[^.!?\n]{20,260}[.!?]?", re.M)
            stop = {"the","and","for","with","that","this","from","were","have","has","had","was","are","is","not","did","does","their","they","there","into","about","than","then","also","after","before","more","less","very","only","its","his","her","our","you","your","de","la","el","los","las","que","con","por","para","una","un","del","se","en","es","no","fue","son","como","más","menos","una"}
            def topic(text: str) -> set[str]:
                words = re.findall(r"[A-Za-zÀ-ÿ]{3,}", text.lower())
                return {w for w in words if w not in stop}
            for index, item in enumerate(items, 1):
                content = str(item.get("page_evidence") or "")
                source_key = str(item.get("url") or f"source-{index}")
                for sentence in sentence_re.findall(content):
                    numbers = re.findall(r"(?<![\w])(?:20\d{2}|\d+(?:[.,]\d+)?%?)(?![\w])", sentence)
                    dates = re.findall(r"\b20\d{2}(?:-\d{2}-\d{2})?\b", sentence)
                    values = list(dict.fromkeys(numbers + dates))
                    if values:
                        records.append({"source": source_key, "index": index, "topic": topic(re.sub(r"\d+(?:[.,]\d+)?%?", " ", sentence)), "values": values, "text": sentence.strip()[:300], "negative": bool(negation.search(sentence))})
            conflicts = []
            for left in records:
                for right in records:
                    if left["index"] >= right["index"] or left["source"] == right["source"]:
                        continue
                    overlap = len(left["topic"] & right["topic"]) / max(1, len(left["topic"] | right["topic"]))
                    if overlap < 0.45:
                        continue
                    if set(left["values"]) == set(right["values"]) and left["negative"] == right["negative"]:
                        continue
                    if set(left["values"]) != set(right["values"]) or left["negative"] != right["negative"]:
                        conflicts.append({
                            "type": "claim_disagreement",
                            "sources": [left["source"], right["source"]],
                            "values": sorted(set(left["values"]) | set(right["values"]))[:8],
                            "polarity_difference": left["negative"] != right["negative"],
                            "contexts": [left["text"], right["text"]],
                        })
                    if len(conflicts) >= 12:
                        return conflicts
            return conflicts

        conflicts = conflict_candidates(verified)
        return {
            "ok": bool(enriched),
            **result,
            "evidence": evidence,
            "verified_evidence_count": len(verified),
            "discovery_result_count": len(enriched),
            "conflict_detected": bool(conflicts),
            "conflict_candidates": conflicts,
        }

    @staticmethod
    def _weather_location(message: str) -> str:
        text = re.sub(r"[?!.]+", " ", message).strip()
        known = re.search(r"\b(esteio|porto alegre)\b", text, re.I)
        return known.group(1) if known else text

    @staticmethod
    def _weather_condition(code: Any) -> str:
        try:
            code = int(code)
        except (TypeError, ValueError):
            return ""
        mapping = {0:"Despejado",1:"Principalmente despejado",2:"Parcialmente nublado",3:"Nublado",45:"Niebla",48:"Niebla con escarcha",51:"Llovizna ligera",53:"Llovizna moderada",55:"Llovizna intensa",61:"Lluvia ligera",63:"Lluvia moderada",65:"Lluvia intensa",71:"Nieve ligera",73:"Nieve moderada",75:"Nieve intensa",80:"Chubascos ligeros",81:"Chubascos moderados",82:"Chubascos intensos",95:"Tormenta",96:"Tormenta con granizo ligero",99:"Tormenta con granizo fuerte"}
        return mapping.get(code, "")

    async def _weather(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        location_query = self._weather_location(message)
        async with httpx.AsyncClient(timeout=12.0) as client:
            geo = await client.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": location_query, "count": 5, "language": "pt", "format": "json"})
            geo.raise_for_status()
            locations = geo.json().get("results") or []
            if not locations:
                return {"ok": False, "available": False, "error": "location_not_found", "query": location_query}
            location = locations[0]
            lat, lon = location.get("latitude"), location.get("longitude")
            weather = await client.get("https://api.open-meteo.com/v1/forecast", params={"latitude": lat, "longitude": lon, "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code", "timezone": "auto", "forecast_days": 1})
            weather.raise_for_status()
            current = weather.json().get("current") or {}
        condition = self._weather_condition(current.get("weather_code"))
        evidence = (
            f"WEATHER SOURCE: Open-Meteo\nLOCATION: {location.get('name')}, {location.get('admin1') or ''}, {location.get('country') or ''}\n"
            f"OBSERVATION TIME: {current.get('time', 'unknown')}\nTEMPERATURE: {current.get('temperature_2m', 'unknown')} °C\n"
            f"APPARENT TEMPERATURE: {current.get('apparent_temperature', 'unknown')} °C\nRELATIVE HUMIDITY: {current.get('relative_humidity_2m', 'unknown')}%\n"
            f"WIND SPEED: {current.get('wind_speed_10m', 'unknown')} km/h\nCONDITION: {condition or 'no disponible'}"
        )
        return {"ok": True, "available": True, "source": "open-meteo", "location": {"name": location.get("name"), "country": location.get("country"), "admin1": location.get("admin1"), "latitude": lat, "longitude": lon}, "current": current, "evidence": evidence}


def normalize_natural_math(text: str) -> str:
    s = text.strip().lower().replace(",", ".").rstrip("?").strip()
    s = re.sub(r"^cu[aá]nto\s+es\s+", "", s)
    s = re.sub(r"\bpor ciento de\b", "% de", s)
    match = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)\s*%\s*de\s*([-+]?\d+(?:\.\d+)?)", s)
    if match:
        return f"({match.group(2)}) * ({match.group(1)}) / 100"
    match = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)\s+por\s+([-+]?\d+(?:\.\d+)?)", s)
    if match:
        return f"({match.group(1)}) * ({match.group(2)})"
    replacements = [
        (r"\s+m[aá]s\s+", " + "),
        (r"\s+menos\s+", " - "),
        (r"\s+entre\s+", " / "),
        (r"\s+dividido\s+por\s+", " / "),
        (r"\s+dividido\s+", " / "),
        (r"\s+multiplicado\s+por\s+", " * "),
        (r"\s+por\s+", " * "),
        (r"\s+x\s+", " * "),
    ]
    for pattern, repl in replacements:
        s = re.sub(pattern, repl, s)
    return s


def safe_calculate(expression: str) -> float:
    tree = parse(expression.strip().replace("^", "**"), mode="eval")
    allowed = (Add, Sub, Mult, Div, Pow, Mod, USub, UAdd)

    def walk(node: Any) -> float:
        if isinstance(node, Expression):
            return walk(node.body)
        if isinstance(node, Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
        if isinstance(node, UnaryOp) and isinstance(node.op, (USub, UAdd)):
            return -walk(node.operand) if isinstance(node.op, USub) else walk(node.operand)
        if isinstance(node, BinOp) and isinstance(node.op, allowed):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, Add): return left + right
            if isinstance(node.op, Sub): return left - right
            if isinstance(node.op, Mult): return left * right
            if isinstance(node.op, Div): return left / right
            if isinstance(node.op, Pow): return left ** right
            return left % right
        raise ValueError("unsupported_expression")

    return walk(tree)
