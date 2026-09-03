from __future__ import annotations

from ast import Expression, Constant, BinOp, UnaryOp, Add, Sub, Mult, Div, Pow, Mod, USub, UAdd, parse
from dataclasses import dataclass
import re
from typing import Any, Awaitable, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    capabilities: tuple[str, ...]
    handler: Callable[..., Awaitable[dict[str, Any]]]


class ToolOrchestrator:
    """Autonomous capability router for Bitey IA.

    Models are generators, not authority. If a registered capability can fulfill
    the request, Bitey attempts that capability before allowing a model to claim
    that the task cannot be performed.
    """

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)
    RESEARCH_TERMS = (
        "investiga", "investigar", "busca", "buscar", "fuentes", "fuente",
        "compara", "comparar", "contrasta", "verifica", "verificar", "research",
        "evidence", "actual", "actualizado", "actualizada", "hoy", "último",
        "última", "ultimo", "latest", "current", "precio", "cotización", "cotizacion",
        "noticias", "qué pasó", "que paso", "información actual", "informacion actual",
    )
    EXTERNAL_DATA_TERMS = (
        "en internet", "en la web", "en línea", "online", "web", "internet",
        "sitio", "página", "pagina", "documentación", "documentacion",
    )

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def available(self) -> list[dict[str, Any]]:
        return [{"name": s.name, "description": s.description, "capabilities": list(s.capabilities)} for s in self._tools.values()]

    def select(self, message: str, context: dict[str, Any] | None = None) -> list[str]:
        """Select tools from intent, freshness, explicit URLs and task semantics.

        Selection is deliberately broader than a few magic words: current or
        externally-grounded questions should trigger research even when the
        user does not explicitly say 'search'.
        """
        q = message.lower()
        selected: list[str] = []
        explicit_url = bool(self.URL_RE.search(message))
        research_context = bool((context or {}).get("research"))
        freshness = any(x in q for x in self.RESEARCH_TERMS)
        external = any(x in q for x in self.EXTERNAL_DATA_TERMS)

        if explicit_url or research_context or freshness or external:
            selected.append("web_research")
        if any(x in q for x in ("archivo", "documento", "pdf", "imagen", "fichero")):
            selected.append("workspace_files")
        if re.search(r"\d+\s*[+\-*/%^]\s*\d+", q) or any(x in q for x in ("calcula", "cálculo", "calculo", "porcentaje", "cuánto", "cuanto", "math")):
            selected.append("calculator")
        if any(x in q for x in ("código", "codigo", "programa", "python", "javascript", "debug", "error", "github", "api")):
            selected.append("code_reasoning")
        return list(dict.fromkeys(selected))

    async def execute(self, names: list[str], **kwargs: Any) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for name in names:
            tool = self._tools.get(name)
            if not tool:
                results[name] = {"ok": False, "error": "capability_not_registered"}
                continue
            try:
                results[name] = await tool.handler(**kwargs)
            except Exception as exc:
                results[name] = {"ok": False, "error": type(exc).__name__}
        return results

    def capability_available(self, name: str) -> bool:
        return name in self._tools


def safe_calculate(expression: str) -> float:
    """Evaluate simple arithmetic only; no names, calls, attributes or code execution."""
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
