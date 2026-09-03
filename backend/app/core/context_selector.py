from __future__ import annotations

import re
from typing import Any

TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
ESSENTIAL_KEYS = ("user_query", "current_message", "goals", "constraints")
ORDER = ESSENTIAL_KEYS + ("conversation", "memory", "learned_cognitive_context", "evidence", "sources", "tools", "module_routing")


def _string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return " ".join(f"{k}: {_string(v)}" for k, v in value.items()).strip()
    if isinstance(value, (list, tuple, set)):
        return " | ".join(_string(v) for v in value if _string(v)).strip()
    return str(value).strip()


def tokens(value: Any) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(_string(value)) if len(t) > 2}


def _items(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [f"{k}: {_string(v)}" for k, v in value.items()]
    if isinstance(value, (list, tuple, set)):
        return [_string(v) for v in value if _string(v)]
    text = _string(value)
    return [text] if text else []


def select_context(source: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    query_tokens = tokens(source.get("user_query") or source.get("current_message"))
    selected: dict[str, Any] = {}
    scores: dict[str, float] = {}
    for key in ORDER:
        if key not in source or not _string(source[key]):
            continue
        overlap = len(query_tokens & tokens(source[key]))
        scores[key] = (1000.0 if key in ESSENTIAL_KEYS else 100.0) + overlap * 25
        selected[key] = source[key]
    for key, value in source.items():
        if key.startswith("_") or key in selected or not _string(value):
            continue
        overlap = len(query_tokens & tokens(value))
        if overlap:
            scores[key] = 50.0 + overlap * 20
            selected[key] = value
    return selected, {"scores": scores, "query_tokens": sorted(query_tokens)}


def compact_value(value: Any, limit: int) -> str:
    items = _items(value)
    if not items or limit <= 0:
        return ""
    if sum(len(i) + 3 for i in items) <= limit:
        return " | ".join(items)
    out: list[str] = []
    used = 0
    for item in items:
        if used + len(item) + 3 > limit:
            break
        out.append(item)
        used += len(item) + 3
    return " | ".join(out) if out else _string(value)[:limit]


def essential_coverage(selected: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    present = [k for k in ESSENTIAL_KEYS if _string(source.get(k))]
    preserved = [k for k in present if _string(selected.get(k))]
    missing = [k for k in present if k not in preserved]
    return {"required": present, "preserved": preserved, "missing": missing, "ok": not missing}
