from __future__ import annotations

from ast import Expression, Constant, BinOp, UnaryOp, Add, Sub, Mult, Div, Pow, Mod, USub, UAdd, parse
from dataclasses import dataclass
import re
from typing import Any, Awaitable, Callable

from .autonomous_language_orchestrator import AutonomousLanguageOrchestrator

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    capabilities: tuple[str, ...]
    handler: Callable[..., Awaitable[dict[str, Any]]]

class ToolOrchestrator:
    """Runtime capability authority driven by language intent, not model claims."""
    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)
    LEGACY_HINTS = {
        "weather": ("tiempo", "clima", "temperatura", "pronóstico", "pronostico", "lluvia", "humedad", "viento", "weather", "forecast"),
        "web_research": ("investiga", "investigar", "busca", "buscar", "fuentes", "compara", "contrasta", "verifica", "research", "evidence", "actual", "hoy", "latest", "current", "precio", "noticias", "internet", "web"),
        "workspace_files": ("archivo", "documento", "pdf", "imagen", "fichero", "file", "document"),
        "calculator": ("calcula", "cálculo", "calculo", "porcentaje", "math"),
        "code_reasoning": ("código", "codigo", "python", "javascript", "programa", "debug", "github", "api", "error"),
    }
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self.language_planner = AutonomousLanguageOrchestrator()
    def register(self, spec: ToolSpec) -> None: self._tools[spec.name] = spec
    def available(self) -> list[dict[str, Any]]: return [{"name": s.name, "description": s.description, "capabilities": list(s.capabilities)} for s in self._tools.values()]
    def select(self, message: str, context: dict[str, Any] | None = None) -> list[str]:
        ctx = context or {}
        plan = ctx.get("language_plan")
        if not isinstance(plan, dict):
            plan = self.language_planner.plan(message, ctx).as_dict()
            ctx["language_plan"] = plan
        selected = [name for name in plan.get("capabilities", []) if name in self._tools]
        if not selected:
            q = message.lower()
            for name, hints in self.LEGACY_HINTS.items():
                if name in self._tools and any(h in q for h in hints): selected.append(name)
            if self.URL_RE.search(message) and "web_research" in self._tools and "web_research" not in selected: selected.append("web_research")
        return list(dict.fromkeys(selected))
    async def execute(self, names: list[str], **kwargs: Any) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for name in names:
            tool = self._tools.get(name)
            if not tool: results[name] = {"ok": False, "error": "capability_not_registered"}; continue
            try: results[name] = await tool.handler(**kwargs)
            except Exception as exc: results[name] = {"ok": False, "error": type(exc).__name__}
        return results
    def capability_available(self, name: str) -> bool: return name in self._tools

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
