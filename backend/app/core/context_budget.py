from __future__ import annotations

from typing import Any

from .context_selector import ESSENTIAL_KEYS, compact_value, essential_coverage, select_context

DEFAULT_CHAR_BUDGET = 9000


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else str(value or "").strip()


def _size(payload: dict[str, Any]) -> int:
    return sum(len(str(k)) + len(_text(v)) + 8 for k, v in payload.items())


def build_context(provider_name: str, context: dict[str, Any] | None, budget: int = DEFAULT_CHAR_BUDGET) -> dict[str, Any]:
    source = dict(context or {})
    selected, meta = select_context(source)
    essentials = [k for k in ESSENTIAL_KEYS if _text(source.get(k))]
    per_essential = max(256, (budget // 2) // max(1, len(essentials))) if essentials else 0
    result: dict[str, Any] = {}
    for key in ESSENTIAL_KEYS:
        if key in selected:
            result[key] = compact_value(selected[key], per_essential)
    remaining = max(0, budget - _size(result))
    dynamic = [k for k in selected if k not in ESSENTIAL_KEYS]
    dynamic.sort(key=lambda k: meta["scores"].get(k, 0), reverse=True)
    for key in dynamic:
        if remaining < 80:
            break
        value = compact_value(selected[key], max(80, remaining - len(key) - 8))
        if value:
            result[key] = value
            remaining = max(0, remaining - len(key) - len(value) - 8)
    coverage = essential_coverage(result, source)
    result["_transport"] = {
        "provider": provider_name,
        "char_budget": budget,
        "selected": list(result.keys()),
        "compacted": _size(source) > _size(result),
        "coverage_ok": coverage["ok"],
        "coverage_missing": coverage["missing"],
        "selection_relevance": meta["scores"],
    }
    return result
