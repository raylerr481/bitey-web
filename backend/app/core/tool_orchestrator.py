from __future__ import annotations

from ast import Expression, Constant, BinOp, UnaryOp, Add, Sub, Mult, Div, Pow, Mod, USub, UAdd, parse
from dataclasses import dataclass
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
    WEATHER_RE = re.compile(r"\b(temperatura|clima|tiempo|weather|temperature|forecast|previs[aã]o)\b", re.I)
    SEARCH_RE = re.compile(r"\b(busca|buscar|búsqueda|investiga|investigar|fuentes|compara|contrasta|search|research|latest|actual|hoy|noticias|news)\b", re.I)
    FRESH_RE = re.compile(r"\b(ahora|ahora mismo|actualmente|actual|hoy|esta semana|este mes|últim[oa]s?|reciente|recientemente|en vivo|tiempo real|live|today|latest|current|recent|this week|this month)\b", re.I)
    WEB_FACT_RE = re.compile(r"\b(precio|precios|cotizaci[oó]n|disponibilidad|horario|direcci[oó]n|versi[oó]n|release|documentaci[oó]n|ley|leyes|regulaci[oó]n|reglamento|elecciones|resultados|ranking|clasificaci[oó]n|estad[ií]sticas|mercado|acciones|noticias|fuente|fuentes|comparar|compara|contrasta|rese[nñ]a|reviews?|who is|what is|how much|where|when|who|what|which)\b", re.I)
    QUESTION_RE = re.compile(r"^\s*(qu[eé]|qui[eé]n|cu[aá]l|cu[aá]les|c[oó]mo|d[oó]nde|cu[aá]ndo|por qu[eé]|what|who|which|where|when|why|how)\b", re.I)

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._cognition = CognitiveModel()
        self._brain = BiteyBrain()
        self.register(ToolSpec("search", "Buscador web general de Bitey mediante DuckDuckGo y recuperación segura de evidencia.", ("web", "search", "research", "evidence"), self._search))
        self.register(ToolSpec("weather", "Consulta meteorología actual mediante Open-Meteo, como fuente especializada del buscador.", ("weather", "current", "forecast"), self._weather))

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def available(self) -> list[dict[str, Any]]:
        return [{"name": s.name, "description": s.description, "capabilities": list(s.capabilities)} for s in self._tools.values()]

    def cognitive_selection(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Produce the executive tool decision before any tool is executed."""
        ctx = dict(context or {})
        cognitive = self._cognition.process(message, ctx, evidence_available=bool(ctx.get("evidence_available")))
        ctx["cognition"] = cognitive.as_dict()
        ctx["_cognitive_state"] = cognitive
        brain = self._brain.think(message, ctx)
        ctx["bitey_brain"] = brain.as_dict()
        ctx["_bitey_brain_state"] = brain
        requested = list(brain.tool_priority)
        if brain.freshness_required and brain.task_class == "weather":
            requested = ["weather"]
        elif brain.evidence_required and "search" not in requested:
            requested.append("search")
        available = set(self._tools)
        selected = [name for name in dict.fromkeys(requested) if name in available]
        if context is not None:
            context["cognition"] = cognitive.as_dict()
            context["_cognitive_state"] = cognitive
            context["bitey_brain"] = brain.as_dict()
            context["_bitey_brain_state"] = brain
            context["selected_tools"] = selected
        return {"cognition": cognitive.as_dict(), "brain": brain.as_dict(), "selected_tools": selected}

    @classmethod
    def needs_web_research(cls, message: str, context: dict[str, Any] | None = None) -> bool:
        """Compatibility helper; final selection is executive-cognition driven."""
        ctx = context or {}
        if bool(ctx.get("requires_web_research") or ctx.get("needs_web") or ctx.get("freshness_required")):
            return True
        return bool(cls.URL_RE.search(message) or cls.SEARCH_RE.search(message) or cls.FRESH_RE.search(message) or cls.WEB_FACT_RE.search(message))

    def select(self, message: str, context: dict[str, Any] | None = None) -> list[str]:
        return self.cognitive_selection(message, context)["selected_tools"]

    async def execute(self, names: list[str], **kwargs: Any) -> dict[str, Any]:
        """Execute selected tools and normalize their evidence into one contract."""
        results: dict[str, Any] = {}
        for name in names:
            tool = self._tools.get(name)
            if not tool:
                continue
            try:
                result = await tool.handler(**kwargs)
                results[name] = result
                if isinstance(result, dict) and result.get("evidence"):
                    existing = results.get("web_research")
                    if not existing or not existing.get("evidence"):
                        results["web_research"] = {"ok": bool(result.get("ok", True)), "reasons": [f"specialized:{name}"], "sources": result.get("source"), "evidence": str(result["evidence"])}
            except Exception as exc:
                results[name] = {"ok": False, "error": type(exc).__name__}
        return results

    async def _search(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        result = await __import__("asyncio").to_thread(general_search, message, 8)
        evidence = "\n\n".join(f"SOURCE {i}: {item.get('url')}\nTITLE: {item.get('title', '')}\nSNIPPET: {item.get('snippet', '')}" for i, item in enumerate((result.get("results") or [])[:8], 1))
        return {"ok": bool(result.get("results")), **result, "evidence": evidence}

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
            payload = weather.json()
            current = payload.get("current") or {}
        units = {"temperature": "°C", "wind_speed": "km/h", "humidity": "%"}
        evidence = (f"WEATHER SOURCE: Open-Meteo\nLOCATION: {location.get('name')}, {location.get('admin1') or ''}, {location.get('country') or ''}\nOBSERVATION TIME: {current.get('time', 'unknown')}\nTEMPERATURE: {current.get('temperature_2m', 'unknown')} °C\nAPPARENT TEMPERATURE: {current.get('apparent_temperature', 'unknown')} °C\nHUMIDITY: {current.get('relative_humidity_2m', 'unknown')} %\nWIND: {current.get('wind_speed_10m', 'unknown')} km/h\nWEATHER CODE: {current.get('weather_code', 'unknown')}")
        return {"ok": True, "available": True, "source": "open-meteo", "location": {"name": location.get("name"), "country": location.get("country"), "admin1": location.get("admin1"), "latitude": lat, "longitude": lon}, "current": current, "units": units, "evidence": evidence}


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
