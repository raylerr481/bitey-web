from __future__ import annotations

from ast import Expression, Constant, BinOp, UnaryOp, Add, Sub, Mult, Div, Pow, Mod, USub, UAdd, parse
from dataclasses import dataclass
import os
import re
import asyncio
from typing import Any, Awaitable, Callable
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

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
    timeout_seconds: float = 20.0
    max_retries: int = 1
    retry_backoff_seconds: float = 0.35


class ToolOrchestrator:
    """Capability executor whose selection follows Bitey's cognitive plan."""

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)
    WEATHER_RE = re.compile(r"\b(temperatur\w*|clima|weather|temperature|forecast|previs[aã]o)\b|\b(?:tiempo|tempo)\s+(?:en|hoy|ahora|hace|est[aá]|está)\b", re.I)
    SEARCH_RE = re.compile(r"\b(busca|buscar|búsqueda|investiga|investigar|fuentes|compara|contrasta|search|research|latest|actual|hoy|noticias|news)\b", re.I)
    FRESH_RE = re.compile(r"\b(ahora|ahora mismo|actualmente|actual|hoy|esta semana|este mes|últim[oa]s?|reciente|recientemente|en vivo|tiempo real|live|today|latest|current|recent|this week|this month)\b", re.I)
    # Broad interrogatives do not automatically require web research.
    # Stable questions can use model knowledge; explicit current/research signals
    # still route to evidence.
    WEB_FACT_RE = re.compile(r"\b(precio|precios|cotizaci[oó]n|disponibilidad|horario|direcci[oó]n|versi[oó]n|release|documentaci[oó]n|ley|leyes|regulaci[oó]n|reglamento|elecciones|resultados|ranking|clasificaci[oó]n|estad[ií]sticas|noticias|fuente|fuentes|comparar|compara|contrasta|rese[nñ]a|reviews?)\b", re.I)
    TRADING_RE = re.compile(r"\b(?:[A-Z]{2,12}(?:USDT|USD)|[A-Z]{6}|XAUUSD|XAGUSD)\b|\b(?:M1|M3|M5|M15|M30|H1|H4|D1|W1|MN1)\b", re.I)
    TURTLE_RE = re.compile(r"\b(?:turtle|tortuga|turtle trading|s1|s2|campa(?:gn|[ñn]a)|piramid(?:e|ing)|unidades?|n/?atr|risk gate|turtle controller)\b", re.I)
    TURTLE_FOLLOWUP_RE = re.compile(r"^\s*(?:¿?y\s+ahora|ahora|¿?y\s+(?:el|la|los|las)\s+(?:equity|balance|señal|signal|riesgo|posición|posicion|trade|trades|turtle)|¿?qué\s+pasó|¿?que\s+paso|¿?cómo\s+va|¿?como\s+va|¿?y\s+(?:después|despues)|¿?y\s+entonces)\s*\??\s*$", re.I)
    SBT_FOLLOWUP_RE = re.compile(r"^\s*(?:¿?y\s+ahora|ahora|¿?qué\s+pasó|¿?que\s+paso|¿?cómo\s+va|¿?como\s+va|¿?y\s+(?:después|despues)|¿?y\s+entonces|¿?qué\s+está\s+haciendo|¿?que\s+esta\s+haciendo)\s*\??\s*$", re.I)\n    MATH_RE = re.compile(r"^\s*(?:\(?\s*[-+]?\d+(?:\.\d+)?\s*\)?\s*(?:[+\-*/%^]\s*\(?\s*[-+]?\d+(?:\.\d+)?\s*\)?\s*)+)$")
    NATURAL_MATH_RE = re.compile(r"^\s*(?:cu[aá]nto\s+es\s+)?[-+]?\d+(?:[.,]\d+)?\s*(?:%\s+de|por ciento de|\+|menos|m[aá]s|por|entre|dividido(?:\s+por)?|multiplicado(?:\s+por)?|x)\s+[-+]?\d+(?:[.,]\d+)?\s*\??\s*$", re.I)

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._cognition = CognitiveModel()
        self._brain = BiteyBrain()
        self.register(ToolSpec("web_research", "Buscador web general de Bitey mediante DuckDuckGo y recuperación segura de evidencia.", ("web", "search", "research", "evidence"), self._search))
        self.register(ToolSpec("search", "Compatibility alias for Bitey web research.", ("web", "search", "research", "evidence"), self._search))
        self.register(ToolSpec("weather", "Consulta meteorología actual mediante Open-Meteo, como fuente especializada del buscador.", ("weather", "current", "forecast"), self._weather))
        self.register(ToolSpec("sbt_market", "Consulta el mercado SBT y ejecuta inteligencia técnica únicamente con datos verificables; no ejecuta órdenes.", ("trading", "market_intelligence", "market_data", "risk"), self._sbt_market))
        self.register(ToolSpec("sbt_turtle", "Consulta el estado real del Turtle Controller en SBT; solo lectura y sin ejecución de órdenes.", ("trading", "turtle", "state", "risk", "evidence"), self._sbt_turtle, timeout_seconds=12.0, max_retries=1))
        self.register(ToolSpec("sbt_ai_context", "Consulta el contexto general del bot activo en MT4 y el estado del AI Bot Lab de SBT; solo lectura.", ("trading", "mt4", "bot", "sbt", "ai_bot_lab", "state", "evidence"), self._sbt_ai_context, timeout_seconds=12.0, max_retries=1))
        self.register(ToolSpec("calculator", "Calculadora local determinista para expresiones aritméticas simples; no requiere proveedor externo.", ("math", "calculation"), self._calculator))
        self.register(ToolSpec("time", "Hora actual para una ubicación explícita usando zonas horarias IANA.", ("time", "current"), self._time))
        self.register(ToolSpec("local_search", "Búsqueda localizada mediante el motor web de Bitey.", ("local_search", "web", "search"), self._local_search))
        self.register(ToolSpec("url_fetch", "Recuperación segura del contenido de una URL proporcionada por el usuario.", ("url", "web", "evidence"), self._url_fetch))
        self.register(ToolSpec("file_context", "Usa contenido de archivos ya adjuntado al contexto de la conversación.", ("files", "documents", "context"), self._file_context))
        self.register(ToolSpec("code_reasoning", "Análisis estructural local y seguro de código proporcionado en el contexto.", ("code", "programming", "analysis"), self._code_reasoning))

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def available(self) -> list[dict[str, Any]]:
        return [{"name": s.name, "description": s.description, "capabilities": list(s.capabilities)} for s in self._tools.values()]

    def _policy_tool_candidates(self, context: dict[str, Any]) -> list[str]:
        """Translate the universal cognitive policy into real executable tools."""
        policy = context.get("execution_policy")
        if not isinstance(policy, dict):
            return []
        family = str(policy.get("intent_family") or "").lower()
        capabilities = {str(value).lower() for value in (policy.get("capabilities") or [])}
        mapping = {
            "weather": ["weather"],
            "math": ["calculator"],
            "local_search": ["web_research"],
            "current_info": ["web_research"],
            "research": ["web_research"],
            "comparison": ["web_research"],
            "recommendation": ["web_research"],
            "time": ["time"],
            "programming": ["code_reasoning"],
            "file_analysis": ["file_context"],
        }
        preferred = list(mapping.get(family, []))
        if "weather" in capabilities:
            preferred.insert(0, "weather")
        if "calculator" in capabilities:
            preferred.insert(0, "calculator")
        if "web_research" in capabilities or "search" in capabilities:
            preferred.append("web_research")
        if "local_search" in capabilities:
            preferred.append("local_search")
        if "time" in capabilities:
            preferred.append("time")
        if "file_context" in capabilities or "file_analysis" in capabilities:
            preferred.append("file_context")
        if "url_fetch" in capabilities:
            preferred.append("url_fetch")
        # code_reasoning remains an internal model role, not an executable tool.
        return list(dict.fromkeys(name for name in preferred if name in self._tools))

    def cognitive_selection(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {})
        cognitive = self._cognition.process(message, ctx, evidence_available=bool(ctx.get("evidence_available")))
        ctx["cognition"] = cognitive.as_dict()
        ctx["_cognitive_state"] = cognitive
        brain = self._brain.think(message, ctx)
        ctx["bitey_brain"] = brain.as_dict()
        ctx["_bitey_brain_state"] = brain
        requested = list(brain.tool_priority)
        # The universal execution policy is now connected to real tools.
        # This keeps intent classification and executable capability selection
        # aligned instead of letting lexical heuristics override the plan.
        policy_tools = self._policy_tool_candidates(ctx)
        if policy_tools:
            requested = policy_tools + requested
        normalized = message.casefold().strip()
        arithmetic_request = bool(
            self.MATH_RE.fullmatch(message.strip())
            or self.NATURAL_MATH_RE.fullmatch(message.strip())
        )
        calculation_profile = "calculation" in set(brain.verification_profile or [])

        # Calculator is an executable capability, not merely a label. Use it
        # for deterministic arithmetic only; symbolic math remains model work.
        turtle_context = (
            str(ctx.get("current_intent_domain") or ctx.get("intent_family") or "").lower() in {"trading", "turtle"}
            or "sbt_turtle" in {str(name) for name in (ctx.get("selected_tools") or [])}
            or "sbt_turtle" in {str(name) for name in ((ctx.get("previous_execution_state") or {}).get("executed_tools", []) if isinstance(ctx.get("previous_execution_state"), dict) else [])}
        )
        if arithmetic_request:
            requested = ["calculator"]
        elif self.TURTLE_RE.search(message) or (self.TURTLE_FOLLOWUP_RE.fullmatch(message) and turtle_context):
            requested = ["sbt_turtle"]
        elif re.search(r"\b(?:sbt|bot|ea|expert advisor|mt4|meta trader|metatrader|tradewill|optimiza|optimización|optimizer|ai bot lab|qué está haciendo|que esta haciendo|qué bot está activo|que bot esta activo|qué está optimizando|que esta optimizando)\b", normalized, re.I):
            requested = ["sbt_ai_context"]
        elif str(cognitive.intention.get("domain", "general")).lower() == "trading" and re.search(r"\b(analiza|analizar|backtest|backtesting|estrategia|señal|signal|setup)\b", normalized, re.I):
            requested = ["sbt_market"]
        elif self.WEATHER_RE.search(message) and (
            str(cognitive.intention.get("domain", "general")).lower() == "weather"
            or "weather" in requested
            or "weather" in policy_tools
        ):
            requested = ["weather"]
            if re.search(r"\b(fuente|fuentes|compara|contrasta|corrobora)\b", normalized):
                requested.append("search")
        elif "url_fetch" in brain.required_capabilities and "url_fetch" not in requested:
            requested.insert(0, "url_fetch")
        elif brain.evidence_required and "search" not in requested and "web_research" not in requested:
            requested.append("search")

        # Code reasoning is a model capability, not a public executable tool.
        requested = ["web_research" if name == "search" else name for name in requested if name != "code_reasoning"]
        selected = [name for name in dict.fromkeys(requested) if name in self._tools]
        if context is not None:
            context.update({
                "cognition": cognitive.as_dict(),
                "_cognitive_state": cognitive,
                "bitey_brain": brain.as_dict(),
                "_bitey_brain_state": brain,
                "selected_tools": selected,
                "execution_policy_applied": bool(policy_tools),
            })
        return {
            "cognition": cognitive.as_dict(),
            "brain": brain.as_dict(),
            "selected_tools": selected,
            "execution_policy": ctx.get("execution_policy", {}),
        }

    @classmethod
    def needs_web_research(cls, message: str, context: dict[str, Any] | None = None) -> bool:
        ctx = context or {}
        if cls.MATH_RE.fullmatch(message.strip()) or cls.NATURAL_MATH_RE.fullmatch(message.strip()):
            return False
        if bool(ctx.get("requires_web_research") or ctx.get("needs_web") or ctx.get("freshness_required")):
            return True

        # The executive brain is authoritative about stable conceptual requests.
        # Lexical words such as "precio", "documentación" or "fuentes" must not
        # override a direct/general classification unless the user explicitly
        # requested fresh research, a URL lookup, or another current signal.
        brain = ctx.get("_bitey_brain_state")
        if brain is not None:
            try:
                if (
                    not bool(brain.evidence_required)
                    and not bool(brain.freshness_required)
                    and str(brain.task_class).lower() == "general"
                    and str(brain.reasoning_mode).lower() == "direct"
                ):
                    return bool(cls.URL_RE.search(message) or cls.SEARCH_RE.search(message))
            except Exception:
                pass

        return bool(cls.URL_RE.search(message) or cls.SEARCH_RE.search(message) or cls.FRESH_RE.search(message) or cls.WEB_FACT_RE.search(message))

    def select(self, message: str, context: dict[str, Any] | None = None) -> list[str]:
        return self.cognitive_selection(message, context)["selected_tools"]

    async def _execute_one(self, tool: ToolSpec, **kwargs: Any) -> dict[str, Any]:
        """Execute one tool with bounded timeout/retry and normalized provenance."""
        attempts = max(1, min(int(tool.max_retries) + 1, 3))
        last_error = "tool_execution_failed"
        for attempt in range(1, attempts + 1):
            started = datetime.now().isoformat()
            try:
                payload = await asyncio.wait_for(
                    tool.handler(**kwargs),
                    timeout=max(0.01, float(tool.timeout_seconds)),
                )
                if not isinstance(payload, dict):
                    payload = {"ok": True, "value": payload}
                result = dict(payload)
                result.setdefault("ok", True)
                result["tool"] = tool.name
                result["capabilities"] = list(tool.capabilities)
                result["execution"] = {
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "started_at": started,
                    "timeout_seconds": float(tool.timeout_seconds),
                    "retry": attempt > 1,
                }
                return result
            except asyncio.TimeoutError:
                last_error = "tool_timeout"
            except Exception as exc:
                last_error = type(exc).__name__
            if attempt < attempts:
                await asyncio.sleep(max(0.0, float(tool.retry_backoff_seconds)) * attempt)

        return {
            "ok": False,
            "tool": tool.name,
            "capabilities": list(tool.capabilities),
            "error": last_error,
            "execution": {
                "attempt": attempts,
                "max_attempts": attempts,
                "timeout_seconds": float(tool.timeout_seconds),
            },
        }

    async def execute(self, names: list[str], **kwargs: Any) -> dict[str, Any]:
        """Execute a bounded multi-tool plan while preserving provenance."""
        results: dict[str, Any] = {}
        ordered_names = list(dict.fromkeys(str(name) for name in names if str(name).strip()))

        executed: set[str] = set()
        max_steps = max(1, min(int((kwargs.get("context") or {}).get("max_tool_steps", 4)), 6))
        agent_loop = bool((kwargs.get("context") or {}).get("agent_loop"))
        loop_context = dict(kwargs.get("context") or {})
        verification_required = bool(loop_context.get("verification_required") or loop_context.get("evidence_required"))
        verification_completed = bool(loop_context.get("verification_completed"))
        replans = 0
        stop_reason = "no_tools_selected"
        objective_complete = False

        while ordered_names and len(executed) < max_steps:
            name = ordered_names.pop(0)
            if name in executed:
                continue
            tool = self._tools.get(name)
            if not tool:
                continue

            kwargs["context"] = loop_context
            result = await self._execute_one(tool, **kwargs)
            results[name] = result
            executed.add(name)

            # Persist only a short-lived routing marker derived from the actual
            # tool execution. This is continuity metadata, not evidence.
            if result.get("ok") and name in {"sbt_turtle", "sbt_ai_context"}:
                loop_context["sbt_context_active"] = True
                loop_context["sbt_context_kind"] = "turtle" if name == "sbt_turtle" else "general"
                loop_context["sbt_last_evidence_class"] = str(result.get("evidence_class") or "NO_EVIDENCE")
                loop_context["sbt_last_tool"] = name
            evidence_text = str(result.get("evidence") or result.get("page_evidence") or "").strip()
            if result.get("ok") and evidence_text:
                loop_context["evidence_available"] = True
                loop_context["evidence"] = evidence_text
            if result.get("ok") and result.get("evidence_verified") is True:
                verification_completed = True
                loop_context["verification_completed"] = True

            if agent_loop and len(executed) < max_steps:
                # Feed the result back into cognition. The next tool is selected
                # only when the current result is missing/failed or explicitly
                # signals that additional evidence is needed.
                evidence_text = str(result.get("evidence") or result.get("page_evidence") or "").strip()
                needs_replan = (
                    not result.get("ok")
                    or bool(result.get("needs_more_evidence"))
                    or bool(result.get("verification_required"))
                    or (verification_required and not verification_completed and bool(evidence_text))
                )
                # A successful, verified evidence result satisfies an evidence gate.
                # Do not keep calling tools merely because the generic agent loop is enabled.
                if verification_required and result.get("ok") and evidence_text and verification_completed:
                    ordered_names = []
                    objective_complete = True
                    stop_reason = "verified_objective_complete"
                elif needs_replan:
                    loop_context = dict(kwargs.get("context") or {})
                    loop_context.update({
                        "evidence_available": bool(evidence_text),
                        "evidence": evidence_text,
                        "executed_tools": list(executed),
                        "agent_loop": True,
                        "max_tool_steps": max_steps,
                        "replan_trigger": "tool_result_insufficient",
                    })
                    try:
                        replans += 1
                        decision = self.cognitive_selection(str(kwargs.get("message") or ""), loop_context)
                        replanned = decision.get("selected_tools") or []
                        for candidate in replanned:
                            if candidate not in executed and candidate not in ordered_names and candidate in self._tools:
                                ordered_names.append(candidate)
                        kwargs["context"] = loop_context
                    except Exception:
                        # Tool replanning is advisory; a failed cognitive retry
                        # must never break the original execution path.
                        pass

            if name == "weather" and not result.get("ok") and "web_research" in self._tools:
                fallback_message = self.weather_fallback_query(
                    str(kwargs.get("message") or ""),
                    locations=list((kwargs.get("context") or {}).get("status_locations") or []),
                )
                fallback = await self._execute_one(
                    self._tools["web_research"],
                    message=fallback_message,
                    context={
                        **(kwargs.get("context") or {}),
                        "weather_fallback": True,
                        "weather_fallback_query": fallback_message,
                    },
                )
                fallback["fallback_from"] = "weather"
                fallback["specialized_tool_error"] = result.get("error") or result.get("reason")
                results["web_research"] = fallback

        if objective_complete:
            stop_reason = stop_reason or "verified_objective_complete"
        elif len(executed) >= max_steps:
            stop_reason = "max_tool_steps_reached"
        elif not ordered_names:
            stop_reason = "no_additional_tools_selected"

        if "web_research" not in results and "search" in results:
            results["web_research"] = results["search"]

        # A failed specialized capability gets one bounded compatible fallback.
        for name, payload in list(results.items()):
            if not isinstance(payload, dict) or payload.get("ok"):
                continue
            fallback_name = None
            if name in {"calculator", "sbt_market"}:
                fallback_name = "web_research"
            if fallback_name and fallback_name not in results and fallback_name in self._tools:
                fallback = await self._execute_one(self._tools[fallback_name], **kwargs)
                fallback["fallback_from"] = name
                fallback["specialized_tool_error"] = payload.get("error") or payload.get("reason")
                results[fallback_name] = fallback
                executed.add(fallback_name)

        # Expose the derived routing marker to the caller's context so the
        # next conversational turn can recognize a genuine SBT continuation.
        caller_context = kwargs.get("context")
        if isinstance(caller_context, dict):
            caller_context.update({
                key: loop_context[key]
                for key in (
                    "sbt_context_active",
                    "sbt_context_kind",
                    "sbt_last_evidence_class",
                    "sbt_last_tool",
                )
                if key in loop_context
            })
            caller_context["executed_tools"] = list(executed)

        if agent_loop:
            results["_agent_loop"] = {
                "enabled": True,
                "objective_complete": objective_complete,
                "stop_reason": stop_reason,
                "steps": len(executed),
                "replans": replans,
                "verification_required": verification_required,
                "verification_completed": verification_completed,
                "executed_tools": list(executed),
            }
        return results

    async def _time(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return deterministic current time for an explicitly named/common location."""
        text = str(message or "").casefold()
        aliases = {
            "são paulo": "America/Sao_Paulo", "sao paulo": "America/Sao_Paulo",
            "porto alegre": "America/Sao_Paulo", "esteio": "America/Sao_Paulo",
            "brasília": "America/Sao_Paulo", "brasilia": "America/Sao_Paulo",
            "new york": "America/New_York", "london": "Europe/London",
            "lisbon": "Europe/Lisbon", "lisboa": "Europe/Lisbon",
            "madrid": "Europe/Madrid", "tokyo": "Asia/Tokyo", "tóquio": "Asia/Tokyo",
        }
        zone = next((tz for name, tz in aliases.items() if name in text), None)
        if not zone:
            return {"ok": False, "error": "location_timezone_not_identified", "evidence": "No se pudo identificar una ubicación explícita para determinar la hora."}
        now = datetime.now(ZoneInfo(zone))
        return {"ok": True, "timezone": zone, "local_time": now.isoformat(), "formatted": now.strftime("%Y-%m-%d %H:%M:%S"), "evidence": f"TIME SOURCE: system timezone database\\nLOCATION TIMEZONE: {zone}\\nLOCAL TIME: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"}

    async def _local_search(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Reuse the verified web retrieval pipeline for location-aware searches."""
        context = dict(context or {})
        context["local_search"] = True
        result = await self._search(message, context)
        if isinstance(result, dict):
            result["tool"] = "local_search"
        return result

    async def _url_fetch(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch a user-supplied URL through the same safe fetch boundary as research."""
        from .search_gateway import safe_fetch
        match = self.URL_RE.search(str(message or ""))
        url = match.group(0).rstrip(".,);]") if match else ""
        if not url:
            return {"ok": False, "error": "url_not_found"}
        parsed = urlparse(url if url.startswith(("http://", "https://")) else "https://" + url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return {"ok": False, "error": "invalid_url"}
        target = url if parsed.scheme in {"http", "https"} else f"https://{url}"
        page = await __import__("asyncio").to_thread(safe_fetch, target, 80000)
        if not page.get("ok"):
            return {"ok": False, "error": "url_fetch_failed", "url": target}
        content = str(page.get("content") or "")[:12000]
        return {"ok": True, "url": target, "title": target, "verified": True, "source_quality": 0.70, "page_evidence": content, "evidence": f"URL SOURCE: {target}\\nEVIDENCE VERIFIED: true\\nCONTENT: {content[:5000]}"}

    async def _file_context(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Consume file text that an upstream attachment/parser already placed in context."""
        context = context or {}
        files = context.get("files") or context.get("file_context") or []
        if isinstance(files, dict): files = [files]
        blocks = []
        for item in files if isinstance(files, list) else []:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("filename") or "file")
                content = str(item.get("content") or item.get("text") or "").strip()
            else:
                name, content = "file", str(item).strip()
            if content: blocks.append(f"FILE: {name}\\nCONTENT: {content[:12000]}")
        if not blocks:
            return {"ok": False, "error": "file_context_unavailable"}
        evidence = "\\n\\n".join(blocks)
        return {"ok": True, "files": len(blocks), "evidence": evidence, "source": "conversation-file-context"}

    async def _code_reasoning(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform bounded deterministic code inspection; synthesis remains model work."""
        context = context or {}
        code = str(context.get("code") or context.get("file_code") or "").strip()
        if not code:
            return {"ok": True, "available": True, "evidence": "CODE ANALYSIS: no code payload was supplied; use the selected code-reasoning model role to analyze the request."}
        findings = []
        if "Traceback (most recent call last)" in code: findings.append("Python traceback detected")
        if re.search(r"\\b(?:TODO|FIXME)\\b", code, re.I): findings.append("TODO/FIXME markers detected")
        if re.search(r"\\b(?:password|api[_-]?key|secret|token)\\s*=", code, re.I): findings.append("possible hard-coded credential assignment")
        if "except Exception:" in code: findings.append("broad exception handler detected")
        return {"ok": True, "available": True, "findings": findings, "evidence": "CODE ANALYSIS: " + ("; ".join(findings) if findings else "no deterministic structural issue detected; deeper reasoning delegated to the code model role.")}

    async def _calculator(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            expression = normalize_natural_math(message)
            value = safe_calculate(expression)
            rendered = str(int(value)) if float(value).is_integer() else str(value)
            return {"ok": True, "value": value, "expression": message.strip(), "source": "local-calculator", "evidence": f"Local deterministic calculation: {message.strip()} = {rendered}"}
        except Exception as exc:
            return {"ok": False, "error": type(exc).__name__, "source": "local-calculator"}

    async def _sbt_ai_context(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Read the general SBT AI Bot Lab context; no trading execution."""
        base_url = os.getenv("SBT_MODULE_URL", "https://bitey-system-bots-trading-api.onrender.com").strip().rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(f"{base_url}/api/v1/ai-bot-lab/context", headers={"Accept": "application/json"})
            if response.status_code >= 400:
                return {"ok": False, "available": False, "verified": False, "execution_enabled": False, "reason": "sbt_ai_context_unavailable", "status_code": response.status_code, "evidence": f"SBT AI Bot Lab returned HTTP {response.status_code}. No active bot was inferred."}
            payload = response.json()
            bot = payload.get("bot") or {}
            connected = bool((payload.get("mt4") or {}).get("connected") or bot.get("connected"))
            if not connected:
                return {"ok": True, "available": True, "verified": False, "execution_enabled": False, "source": "sbt_ai_bot_lab", "observed": False, "context": payload, "evidence": "SBT AI Bot Lab is reachable, but no MT4 bot snapshot is currently connected. No active bot, account mode, signal, or optimization result was inferred."}
            return {
                "ok": True, "available": True, "verified": True, "evidence_verified": True, "execution_enabled": False,
                "source": "sbt_ai_bot_lab", "observed": True, "bot": bot,
                "analysis": payload.get("analysis") or {},
                "optimization": payload.get("optimization") or {},
                "activity": payload.get("activity") or [],
                "context": payload,
                "evidence": (
                    "SBT AI Bot Lab verified from MT4 context. "
                    f"Bot: {bot.get('name') or 'unknown'}; strategy: {bot.get('strategy') or 'unknown'}; "
                    f"symbol: {bot.get('symbol') or '—'}; timeframe: {bot.get('timeframe') or '—'}; "
                    f"mode: {bot.get('mode') or 'UNKNOWN'}; regime: {bot.get('regime') or 'UNKNOWN'}. "
                    "SBT remains read-only for this Bitey IA capability; parameter application is not automatic."
                ),
            }
        except (httpx.HTTPError, ValueError) as exc:
            return {"ok": False, "available": False, "verified": False, "execution_enabled": False, "reason": "sbt_ai_context_connection_error", "error": type(exc).__name__, "evidence": "Bitey IA could not reach SBT AI Bot Lab. No active bot or optimization state was inferred."}

    async def _sbt_turtle(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Read the SBT Turtle Controller state without creating trading state."""
        base_url = os.getenv("SBT_MODULE_URL", "https://bitey-system-bots-trading-api.onrender.com").strip().rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/api/v1/turtle/context", headers={"Accept": "application/json"})
            if response.status_code >= 400:
                return {"ok": False, "available": False, "verified": False, "execution_enabled": False, "reason": "sbt_turtle_context_unavailable", "status_code": response.status_code, "evidence_class": "TOOL_FAILED", "evidence": f"SBT Turtle context returned HTTP {response.status_code}. No Turtle state was inferred."}
            payload = response.json()
            if str(payload.get("evidence_class") or "NO_EVIDENCE") != "MT4_LIVE_SNAPSHOT" or not bool(payload.get("observed")):
                return {"ok": True, "available": True, "verified": False, "execution_enabled": False, "source": "sbt_turtle_context", "evidence_class": "NO_EVIDENCE", "observed": False, "context": payload, "evidence": "SBT Turtle Controller is reachable, but it has no current MT4 live snapshot. No Turtle state, signal, position, or trade result was inferred."}
            state = payload.get("state") or {}
            return {
                "ok": True, "available": True, "verified": True, "evidence_verified": True, "execution_enabled": False,
                "source": "sbt_turtle_context", "evidence_class": "MT4_LIVE_SNAPSHOT", "observed": True,
                "state": state, "context": payload,
                "evidence": (
                    "SBT Turtle Controller verified from MT4 live snapshot. "
                    f"Symbol: {state.get('symbol') or '—'}; timeframe: {state.get('timeframe') or '—'}; "
                    f"signal: {state.get('signal') or 'NONE'}; next_action: {state.get('next_action') or 'WAIT'}; "
                    f"position_count: {state.get('position_count', 0)}; risk_pct: {state.get('risk_pct', 0)}; "
                    f"drawdown_pct: {state.get('drawdown_pct', 0)}; learning_status: {state.get('learning_status') or 'OBSERVING'}; "
                    f"proposal_pending: {bool(state.get('proposal_pending'))}. Execution authority: SBT Risk Gate."
                ),
            }
        except (httpx.HTTPError, ValueError) as exc:
            return {"ok": False, "available": False, "verified": False, "execution_enabled": False, "reason": "sbt_turtle_connection_error", "error": type(exc).__name__, "evidence_class": "TOOL_FAILED", "evidence": "Bitey IA could not reach SBT Turtle Controller. No Turtle state was inferred and no execution was attempted."}

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

    @staticmethod
    def _source_relevance(message: str, item: dict[str, Any]) -> float:
        """Score whether a retrieved source actually addresses the user's request."""
        stop = {
            "para","como","cual","cuál","que","qué","donde","dónde","cuando","cuándo",
            "este","esta","esto","sobre","desde","hace","hoy","ahora","with","from",
            "what","where","when","this","that","about","latest","current","please",
        }
        def tokens(value: str) -> set[str]:
            return {
                token for token in re.findall(r"[a-záéíóúüñ0-9]{3,}", value.casefold())
                if token not in stop
            }
        query_terms = tokens(message)
        if not query_terms:
            return 0.0
        title_url = tokens(f"{item.get('title','')} {item.get('url','')}")
        evidence = tokens(str(item.get("page_evidence") or item.get("evidence") or "")[:12000])
        title_overlap = len(query_terms & title_url) / len(query_terms)
        evidence_overlap = len(query_terms & evidence) / len(query_terms)
        score = (title_overlap * 0.70) + (evidence_overlap * 0.30)
        return round(min(1.0, score), 4)


    async def _search(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        import asyncio
        from urllib.parse import urlparse
        from .search_gateway import safe_fetch

        # Resolve short follow-ups against the previous researched subject before web retrieval.
        # The current message remains authoritative; prior context only supplies the missing referent.
        search_message = str(message or "").strip()
        prior = context.get("previous_result_context") if isinstance(context, dict) else {}
        prior_query = str(prior.get("query") or "").strip() if isinstance(prior, dict) else ""
        follow_up = bool(re.search(
            r"\\b(?:segunda|segundo|tercera|tercero|primera|primero|opción|opcion|fuente|fuentes|"
            r"esa|ese|eso|aquella|aquel|anterior|arriba|abajo|continúa|continua|y ahora|qué pasa con|que pasa con)\\b",
            search_message, re.I,
        ))
        if follow_up and prior_query and len(search_message.split()) <= 18:
            search_message = f"{prior_query} {search_message}".strip()
        result = await asyncio.to_thread(general_search, search_message, 8)
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

        # Relevance is a hard evidence boundary: a verified page is not useful
        # merely because it contains one lexical match. Rank by request overlap
        # and suppress clearly unrelated pages before they reach the LLM or UI.
        verified = []
        for item in enriched:
            if not item.get("evidence_verified") or not item.get("page_evidence"):
                continue
            relevance = self._source_relevance(message, item)
            item["relevance"] = relevance
            verified.append(item)
        verified_count = len(verified)
        verified_for_provenance = list(verified)
        verified.sort(
            key=lambda item: (
                float(item.get("relevance", 0.0)),
                float(item.get("source_quality", 0.0)),
            ),
            reverse=True,
        )
        relevant_verified = [item for item in verified if float(item.get("relevance", 0.0)) >= 0.08]
        verified = relevant_verified[:6]
        evidence_candidates = verified if verified else verified_for_provenance[:1]
        result["results"] = [
            item for item in enriched
            if float(item.get("relevance", 0.0) or 0.0) >= 0.08
        ][:8]
        evidence_blocks = []
        for i, item in enumerate(evidence_candidates, 1):
            evidence_blocks.append(
                f"SOURCE {i}: {item.get('url')}\n"
                f"TITLE: {item.get('title', '')}\n"
                f"SOURCE QUALITY: {item.get('source_quality', 0.0):.2f} ({item.get('source_category', 'unknown')})\n"
                f"EVIDENCE VERIFIED: true\n"
                f"CONTENT: {str(item.get('page_evidence'))[:5000]}"
            )
        evidence = "\n\n".join(evidence_blocks)

        def conflict_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            """Find conservative cross-source disagreements about the same claim."""
            records: list[dict[str, Any]] = []
            negation = re.compile(
                r"\\b(?:no|not|never|without|did not|does not|cannot|can't|isn't|aren't|wasn't|weren't|no es|no son|no fue|no hay|nunca|sin)\\b",
                re.I,
            )
            sentence_re = re.compile(r"[^.!?\\n]{20,260}[.!?]?", re.M)
            stop = {
                "the","and","for","with","that","this","from","were","have","has","had","was","are","is",
                "not","did","does","their","they","there","into","about","than","then","also","after","before",
                "more","less","very","only","its","his","her","our","you","your","de","la","el","los","las",
                "que","con","por","para","una","un","del","se","en","es","no","fue","son","como","más","menos",
            }

            def tokens(text: str) -> set[str]:
                words = re.findall(r"[A-Za-zÀ-ÿ]{3,}", text.lower())
                return {w for w in words if w not in stop}

            def claim_value(sentence: str) -> tuple[list[str], str]:
                # Keep the unit/category attached to the value so 10% does not
                # conflict with 10 people, dollars, years, etc.
                value_re = re.compile(
                    r"(?<![\\w])(?:20\\d{2}(?:-\\d{2}-\\d{2})?|\\d+(?:[.,]\\d+)?)(?:\\s*(?:%|percent|por ciento|\\$|€|R\\$|USD|EUR|BRL|km/h|km|mi|kg|g|mg|m|cm|mm|million|millions|mil|millones|people|persons|personas|years|a[nñ]os|days|d[ií]as|months|meses))?(?![\\w])",
                    re.I,
                )
                values = [v.strip() for v in value_re.findall(sentence)]
                normalized = []
                for value in values:
                    normalized.append(re.sub(r"\\s+", " ", value.lower().replace(",", ".")))
                unit_re = re.compile(
                    r"(?:%|percent|por ciento|\\$|€|r\\$|usd|eur|brl|km/h|km|mi|kg|g|mg|million|millions|mil|millones|people|persons|personas|years|a[nñ]os|days|d[ií]as|months|meses)",
                    re.I,
                )
                units = [u.lower().replace("r$", "brl") for u in unit_re.findall(sentence)]
                category = " ".join(sorted(set(units)))
                return normalized, category

            for index, item in enumerate(items, 1):
                content = str(item.get("page_evidence") or "")
                source_key = str(item.get("url") or f"source-{index}")
                for sentence in sentence_re.findall(content):
                    values, unit_category = claim_value(sentence)
                    if not values:
                        continue
                    subject = tokens(re.sub(r"(?:20\\d{2}(?:-\\d{2}-\\d{2})?|\\d+(?:[.,]\\d+)?)(?:\\s*(?:%|percent|por ciento|\\$|€|R\\$|USD|EUR|BRL|km/h|km|mi|kg|g|mg|m|cm|mm|million|millions|mil|millones|people|persons|personas|years|a[nñ]os|days|d[ií]as|months|meses))?", " ", sentence))
                    # Very short subjects are too ambiguous for a cross-source conflict.
                    if len(subject) < 2:
                        continue
                    records.append({
                        "source": source_key,
                        "index": index,
                        "subject": subject,
                        "values": values,
                        "unit_category": unit_category,
                        "text": sentence.strip()[:300],
                        "negative": bool(negation.search(sentence)),
                    })

            conflicts: list[dict[str, Any]] = []
            seen: set[tuple[str, str, str, str]] = set()
            for left in records:
                for right in records:
                    if left["index"] >= right["index"] or left["source"] == right["source"]:
                        continue
                    # Compare the same subject, not merely sentences that happen
                    # to share generic words such as "government" or "population".
                    overlap = len(left["subject"] & right["subject"]) / max(1, len(left["subject"] | right["subject"]))
                    shared = len(left["subject"] & right["subject"])
                    if shared < 2 or overlap < 0.60:
                        continue
                    # Numeric conflicts are meaningful only when the value units
                    # are compatible. Empty categories are allowed for plain counts.
                    if left["unit_category"] != right["unit_category"]:
                        continue
                    values_differ = set(left["values"]) != set(right["values"])
                    polarity_differ = left["negative"] != right["negative"]
                    if not values_differ and not polarity_differ:
                        continue
                    key = (
                        min(left["source"], right["source"]),
                        max(left["source"], right["source"]),
                        "|".join(sorted(set(left["values"]) | set(right["values"]))),
                        str(polarity_differ),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    conflicts.append({
                        "type": "claim_disagreement",
                        "sources": [left["source"], right["source"]],
                        "values": sorted(set(left["values"]) | set(right["values"]))[:8],
                        "unit_category": left["unit_category"],
                        "subject_overlap": round(overlap, 3),
                        "polarity_difference": polarity_differ,
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
            "verified_evidence_count": verified_count,
            "relevance_filtered": len(enriched) - len(result["results"]),
            "discovery_result_count": len(enriched),
            "conflict_detected": bool(conflicts),
            "conflict_candidates": conflicts,
        }

    @staticmethod
    def weather_fallback_query(message: str, locations: list[str] | None = None) -> str:
        """Build a narrow meteorological query when the structured weather tool fails."""
        requested = [str(item).strip() for item in (locations or []) if str(item).strip()]
        if not requested:
            requested = [ToolOrchestrator._weather_location(message)]
        normalized: list[str] = []
        for location in requested:
            value = re.sub(r"\borto\s+alegre\b", "porto alegre", location, flags=re.I)
            value = re.sub(r"\bbra(?:s|z)il\b", "Brasil", value, flags=re.I)
            if value and value.casefold() not in {item.casefold() for item in normalized}:
                normalized.append(value)
        return " ; ".join(
            f"weather {place} RS Brazil current conditions"
            for place in normalized
        ) or f"weather {message} Brazil current conditions"

    @staticmethod
    def _weather_location(message: str) -> str:
        text = re.sub(r"[?!.]+", " ", message).strip()
        known = re.search(r"\b(esteio|porto alegre)\b", text, re.I)
        if known:
            return known.group(1)
        # Recover common typing/speech variants before geocoding.
        normalized = re.sub(r"\borto\s+alegre\b", "porto alegre", text, flags=re.I)
        normalized = re.sub(r"\bbra(?:s|z)il\b", "Brasil", normalized, flags=re.I)
        normalized = re.sub(r"\bbrasil\b", " ", normalized, flags=re.I)
        normalized = re.sub(
            r"\b(?:que|qué|como|cómo|esta|está|tiempo|clima|temperatura|hoy|ahora|es|en|in|em)\b",
            " ",
            normalized,
            flags=re.I,
        )
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized or text

    @staticmethod
    def _weather_condition(code: Any) -> str:
        try:
            code = int(code)
        except (TypeError, ValueError):
            return ""
        mapping = {0:"Despejado",1:"Principalmente despejado",2:"Parcialmente nublado",3:"Nublado",45:"Niebla",48:"Niebla con escarcha",51:"Llovizna ligera",53:"Llovizna moderada",55:"Llovizna intensa",61:"Lluvia ligera",63:"Lluvia moderada",65:"Lluvia intensa",71:"Nieve ligera",73:"Nieve moderada",75:"Nieve intensa",80:"Chubascos ligeros",81:"Chubascos moderados",82:"Chubascos intensos",95:"Tormenta",96:"Tormenta con granizo ligero",99:"Tormenta con granizo fuerte"}
        return mapping.get(code, "")

    async def _weather(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        # Resolve every explicit known location so one request can return
        # independently verified conditions for multiple cities.
        context = context or {}
        requested = [
            str(item).strip()
            for item in (context.get("status_locations") or [])
            if str(item).strip()
        ]
        if not requested:
            requested = re.findall(r"\b(?:esteio|porto alegre)\b", message, flags=re.I)
        if not requested:
            requested = [self._weather_location(message)]

        locations_requested: list[str] = []
        for value in requested:
            normalized = re.sub(r"\borto\s+alegre\b", "porto alegre", value, flags=re.I)
            if normalized and normalized.casefold() not in {item.casefold() for item in locations_requested}:
                locations_requested.append(normalized)

        observations: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=12.0) as client:
            for location_query in locations_requested[:5]:
                geo = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": location_query, "count": 5, "language": "pt", "format": "json"},
                )
                geo.raise_for_status()
                geo_locations = geo.json().get("results") or []
                if not geo_locations:
                    continue
                location = geo_locations[0]
                lat, lon = location.get("latitude"), location.get("longitude")
                weather = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
                        "timezone": "auto",
                        "forecast_days": 1,
                    },
                )
                weather.raise_for_status()
                current = weather.json().get("current") or {}
                condition = self._weather_condition(current.get("weather_code"))
                display_name = f"{location.get('name')}, {location.get('admin1') or ''}, {location.get('country') or ''}".strip(" ,")
                evidence = (
                    f"WEATHER SOURCE: Open-Meteo\nLOCATION: {display_name}\n"
                    f"OBSERVATION TIME: {current.get('time', 'unknown')}\n"
                    f"TEMPERATURE: {current.get('temperature_2m', 'unknown')} °C\n"
                    f"APPARENT TEMPERATURE: {current.get('apparent_temperature', 'unknown')} °C\n"
                    f"RELATIVE HUMIDITY: {current.get('relative_humidity_2m', 'unknown')}%\n"
                    f"WIND SPEED: {current.get('wind_speed_10m', 'unknown')} km/h\n"
                    f"CONDITION: {condition or 'no disponible'}"
                )
                observations.append({
                    "name": location.get("name"),
                    "country": location.get("country"),
                    "admin1": location.get("admin1"),
                    "latitude": lat,
                    "longitude": lon,
                    "current": current,
                    "evidence": evidence,
                })
                sources.append({
                    "ok": True,
                    "url": "https://open-meteo.com/",
                    "title": f"Open-Meteo — {location.get('name')} datos meteorológicos",
                    "source_quality": 0.95,
                    "page_evidence": evidence,
                    "evidence_verified": True,
                    "relevance": 1.0,
                    "source": "open-meteo",
                })

        if not observations:
            return {
                "ok": False,
                "available": False,
                "error": "location_or_weather_unavailable",
                "query": locations_requested,
            }

        evidence = "\n\n".join(item["evidence"] for item in observations)
        return {
            "ok": True,
            "available": True,
            "source": "open-meteo",
            "sources": sources,
            "locations": observations,
            "current": observations[0].get("current") if observations else {},
            "evidence": evidence,
        }

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
