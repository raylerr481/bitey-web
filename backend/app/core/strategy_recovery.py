from __future__ import annotations

import re
from typing import Any


def strategy_recovery_plan(
    *,
    objective_gate: dict[str, Any],
    executed_tools: list[str] | None = None,
    tool_results: dict[str, Any] | None = None,
    query: str = "",
    previous_recoveries: list[str] | None = None,
    max_switches: int = 2,
) -> dict[str, Any]:
    """Select one bounded alternate capability after execution failure."""
    gate = objective_gate if isinstance(objective_gate, dict) else {}
    if str(gate.get("objective_status") or "") == "completed":
        return {"required": False, "switch_count": 0, "attempted_strategies": []}

    previous = [
        " ".join(str(item).split())[:500]
        for item in (previous_recoveries or [])
        if str(item).strip()
    ]
    switch_count = sum(item.startswith("switch:") for item in previous)
    if switch_count >= max_switches:
        return {
            "required": False,
            "blocked": True,
            "reason": "strategy_switch_limit_reached",
            "switch_count": switch_count,
            "attempted_strategies": previous[-12:],
            "next_action": {
                "id": "recovery_wait",
                "action": "No quedan rutas alternativas seguras; no repetiré automáticamente la misma estrategia.",
                "kind": "blocked_wait",
            },
        }

    results = tool_results if isinstance(tool_results, dict) else {}
    executed = {str(item).strip() for item in (executed_tools or []) if str(item).strip()}
    failed = {
        str(name)
        for name, value in results.items()
        if isinstance(value, dict) and not value.get("ok")
    }
    has_url = bool(re.search(r"(?:https?://|www\\.)", query, re.I))

    candidates: list[tuple[str, list[str], str]] = []
    if "weather" in failed:
        candidates.append((
            "weather->web_research",
            ["web_research"],
            "La herramienta meteorológica falló; cambiaré a investigación web meteorológica.",
        ))
    if failed.intersection({"web_research", "search"}) and has_url:
        candidates.append((
            "web_research->url_fetch",
            ["url_fetch"],
            "La búsqueda web falló y la consulta incluye una URL; usaré recuperación directa.",
        ))

    for signature, tools, reason in candidates:
        if f"switch:{signature}" in previous:
            continue
        if any(tool in executed for tool in tools):
            continue
        return {
            "required": True,
            "blocked": False,
            "reason": reason,
            "switch_count": switch_count + 1,
            "attempted_strategies": (previous + [f"switch:{signature}"])[-12:],
            "next_action": {
                "id": "strategy_recovery",
                "action": reason,
                "kind": "strategy_switch",
            },
            "tool_override": tools,
            "strategy": signature,
        }

    return {
        "required": False,
        "blocked": True,
        "reason": "no_safe_alternate_strategy",
        "switch_count": switch_count,
        "attempted_strategies": previous[-12:],
        "next_action": {
            "id": "recovery_wait",
            "action": "No existe una ruta alternativa segura con las capacidades disponibles.",
            "kind": "blocked_wait",
        },
    }
