from __future__ import annotations

from ast import Expression, Constant, BinOp, UnaryOp, Add, Sub, Mult, Div, Pow, Mod, USub, UAdd, parse
from dataclasses import dataclass
import re
from typing import Any, Awaitable, Callable

import httpx

from .search_gateway import search as general_search


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    capabilities: tuple[str, ...]
    handler: Callable[..., Awaitable[dict[str, Any]]]


class ToolOrchestrator:
    """General-purpose capability router for Bitey IA, independent of enterprise context.

    Web research is a cross-domain capability, not a weather-only feature. The
    router can trigger it explicitly from context or heuristically when a
    question asks for current, factual, comparative, source-backed, or otherwise
    externally verifiable information.
    """

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)
    WEATHER_RE = re.compile(r"\b(temperatura|clima|tiempo|weather|temperature|forecast|previs[aã]o)\b", re.I)
    SEARCH_RE = re.compile(r"\b(busca|buscar|búsqueda|investiga|investigar|fuentes|compara|contrasta|search|research|latest|actual|hoy|noticias|news)\b", re.I)
    FRESH_RE = re.compile(r"\b(ahora|ahora mismo|actualmente|actual|hoy|esta semana|este mes|últim[oa]s?|reciente|recientemente|en vivo|tiempo real|live|today|latest|current|recent|this week|this month)\b", re.I)
    WEB_FACT_RE = re.compile(r"\b(precio|precios|cotizaci[oó]n|disponibilidad|horario|direcci[oó]n|versi[oó]n|release|documentaci[oó]n|ley|leyes|regulaci[oó]n|reglamento|elecciones|resultados|ranking|clasificaci[oó]n|estad[ií]sticas|mercado|acciones|noticias|fuente|fuentes|comparar|compara|contrasta|rese[nñ]a|reviews?|who is|what is|how much|where|when|who|what|which)\b", re.I)
    QUESTION_RE = re.compile(r"^\s*(qu[eé]|qui[eé]n|cu[aá]l|cu[aá]les|c[oó]mo|d[oó]nde|cu[aá]ndo|por qu[eé]|what|who|which|where|when|why|how)\b", re.I)

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self.register(ToolSpec("search", "Buscador web general de Bitey mediante DuckDuckGo y recuperación segura de evidencia.", ("web", "search", "research", "evidence"), self._search))
        self.register(ToolSpec("weather", "Consulta meteorología actual mediante Open-Meteo, como fuente especializada del buscador.", ("weather", "current", "forecast"), self._weather))

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def available(self) -> list[dict[str, Any]]:
        return [{"name": s.name, "description": s.description, "capabilities": list(s.capabilities)} for s in self._tools.values()]

    @classmethod
    def needs_web_research(cls, message: str, context: dict[str, Any] | None = None) -> bool:
        """Return true when answering from memory alone is unsafe or insufficient."""
        ctx = context or {}
        if bool(ctx.get("requires_web_research") or ctx.get("needs_web") or ctx.get("freshness_required")):
            return True
        if cls.URL_RE.search(message) or cls.SEARCH_RE.search(message) or cls.FRESH_RE.search(message):
            return True
        if cls.WEB_FACT_RE.search(message):
            return True
        # Questions containing a concrete named target often benefit from
        # verification; this deliberately avoids sending ordinary conversational
        # prompts to the web by requiring a factual interrogative form.
        return bool(cls.QUESTION_RE.search(message) and len(message.split()) >= 4 and re.search(r"[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ.-]+", message))

    def select(self, message: str, context: dict[str, Any] | None = None) -> list[str]:
        q = message.lower()
        selected: list[str] = []
        if self.needs_web_research(message, context) or self.URL_RE.search(message):
            selected.append("search")
        if self.WEATHER_RE.search(message):
            selected.append("weather")
        if any(x in q for x in ("archivo", "documento", "pdf", "imagen", "fichero")):
            selected.append("workspace_files")
        if re.search(r"\d+\s*[+\-*/%^]\s*\d+", q) or any(x in q for x in ("calcula", "cálculo", "porcentaje", "cuánto", "cuanto", "math")):
            selected.append("calculator")
        if any(x in q for x in ("código", "codigo", "programa", "python", "javascript", "debug", "error")):
            selected.append("code_reasoning")
        return list(dict.fromkeys(selected))

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
        return results

    async def _search(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        result = await __import__("asyncio").to_thread(general_search, message, 8)
        return {"ok": bool(result.get("results")), **result}

    async def _weather(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        query = message.strip()
        if re.search(r"\b(esteio|porto alegre)\b", query, re.I) and not re.search(r"\b(brasil|brazil)\b", query, re.I):
            query += ", Brasil"
        async with httpx.AsyncClient(timeout=12.0) as client:
            geo = await client.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": query, "count": 5, "language": "pt", "format": "json"})
            geo.raise_for_status()
            locations = geo.json().get("results") or []
            if not locations:
                return {"ok": False, "available": False, "error": "location_not_found", "query": query}
            location = next((x for x in locations if str(x.get("name", "")).lower() in {"esteio", "porto alegre"}), locations[0])
            lat, lon = location.get("latitude"), location.get("longitude")
            weather = await client.get("https://api.open-meteo.com/v1/forecast", params={"latitude": lat, "longitude": lon, "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code", "timezone": "auto", "forecast_days": 1})
            weather.raise_for_status()
            current = weather.json().get("current") or {}
        return {"ok": True, "available": True, "source": "open-meteo", "location": {"name": location.get("name"), "country": location.get("country"), "admin1": location.get("admin1"), "latitude": lat, "longitude": lon}, "current": current, "units": {"temperature": "°C", "wind_speed": "km/h", "humidity": "%"}}


def safe_calculate(expression: str) -> float:
    tree = parse(expression.strip().replace("^", "**"), mode="eval")
    allowed = (Add, Sub, Mult, Div, Pow, Mod, USub, UAdd)
    def walk(node: Any) -> float:
        if isinstance(node, Expression): return walk(node.body)
        if isinstance(node, Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool): return float(node.value)
        if isinstance(node, UnaryOp) and isinstance(node.op, (USub, UAdd)): return -walk(node.operand) if isinstance(node.op, USub) else walk(node.operand)
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
