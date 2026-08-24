from __future__ import annotations

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
    """Selects the minimum useful public/free tool before model generation."""

    URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>'\"]+", re.I)

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def available(self) -> list[dict[str, Any]]:
        return [{"name": s.name, "description": s.description, "capabilities": list(s.capabilities)} for s in self._tools.values()]

    def select(self, message: str, context: dict[str, Any] | None = None) -> list[str]:
        q = message.lower()
        selected: list[str] = []
        if self.URL_RE.search(message) or any(x in q for x in ("investiga", "busca", "fuentes", "compara", "contrasta", "actual", "hoy", "latest", "research")):
            selected.append("web_research")
        if any(x in q for x in ("archivo", "documento", "pdf", "imagen", "fichero")):
            selected.append("workspace_files")
        if any(x in q for x in ("calcula", "cálculo", "porcentaje", "cuánto", "cuanto", "math")):
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
