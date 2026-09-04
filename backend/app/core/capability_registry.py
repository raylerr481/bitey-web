"""Bitey IA capability registry.

The registry is the stable contract between Bitey Brain and workspace modes.
Models may implement a capability, but they do not own capability selection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CapabilitySpec:
    id: str
    name: str
    description: str
    input_types: tuple[str, ...] = ()
    output_types: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    risk: str = "low"
    free_first: bool = True
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "input_types": list(self.input_types),
            "output_types": list(self.output_types),
            "tools": list(self.tools),
            "risk": self.risk,
            "free_first": self.free_first,
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


class CapabilityRegistry:
    """Declarative capability catalog used by the executive cognitive layer."""

    def __init__(self) -> None:
        self._items: dict[str, CapabilitySpec] = {}
        self._register_defaults()

    def register(self, spec: CapabilitySpec) -> None:
        self._items[spec.id] = spec

    def get(self, capability_id: str) -> CapabilitySpec | None:
        return self._items.get(capability_id)

    def available(self) -> list[dict[str, Any]]:
        return [item.as_dict() for item in self._items.values() if item.enabled]

    def resolve(self, *, mode: str | None = None, domain: str | None = None) -> list[CapabilitySpec]:
        mode = (mode or "general").strip().lower()
        domain = (domain or "general").strip().lower()
        if mode not in {"general", "chat"}:
            direct = self.get(mode)
            if direct and direct.enabled:
                return [direct]
        aliases = {
            "trading": "markets",
            "market": "markets",
            "market_intelligence": "markets",
            "research": "research",
            "programming": "developer",
            "code": "developer",
            "web": "websites",
            "automation": "automations",
        }
        candidate = aliases.get(domain, domain)
        selected = self.get(candidate)
        if selected and selected.enabled:
            return [selected]
        general = self.get("general")
        return [general] if general else []

    def _register_defaults(self) -> None:
        specs = [
            ("general", "General", "Conversación, planificación y razonamiento general.", ("text",), ("text",), ("memory", "reasoning")),
            ("research", "Deep Research", "Investigación web acotada, evidencia, contraste y síntesis.", ("text", "url"), ("report", "sources"), ("web_research", "evidence")),
            ("documents", "Documents", "Creación y transformación de documentos editables.", ("text", "file"), ("docx", "pdf", "text"), ("workspace_files",)),
            ("slides", "Slides", "Construcción de presentaciones a partir de objetivos y fuentes.", ("text", "file", "data"), ("pptx", "slides"), ("workspace_files", "research")),
            ("sheets", "Sheets", "Análisis estructurado de datos y hojas de cálculo.", ("data", "file", "text"), ("xlsx", "csv", "analysis"), ("workspace_files", "calculator")),
            ("images", "Images", "Planificación y creación de recursos visuales mediante proveedores disponibles.", ("text", "image"), ("image",), ("image_generation",)),
            ("websites", "Websites / Apps", "Diseño, análisis y evolución de sitios y aplicaciones.", ("text", "file", "code"), ("web", "code"), ("code_reasoning", "workspace_files"), risk="medium"),
            ("developer", "AI Developer", "Análisis y desarrollo de software con ejecución controlada.", ("text", "code", "file"), ("code", "patch", "tests"), ("code_reasoning",), risk="medium"),
            ("video", "Video", "Planificación y producción de contenido audiovisual mediante herramientas disponibles.", ("text", "image", "video"), ("video",), ("video_generation",)),
            ("audio", "Audio / Podcast", "Guion, análisis y producción de audio mediante herramientas disponibles.", ("text", "audio"), ("audio", "podcast"), ("audio_generation",)),
            ("skills", "Skills", "Descubrimiento y composición de habilidades especializadas.", ("text",), ("workflow",), ("skill_registry",)),
            ("automations", "Automations", "Planificación de tareas recurrentes y disparadores controlados.", ("text",), ("task", "schedule"), ("automation_runtime",), risk="medium"),
            ("markets", "Live Markets", "Contexto de mercado y análisis de inteligencia de trading sin ejecución automática.", ("text", "market"), ("market_context", "analysis"), ("sbt_market_data",), risk="high", metadata={"execution_boundary": "sbt_risk_gate", "live_trading": False}),
        ]
        for row in specs:
            self.register(CapabilitySpec(*row))
