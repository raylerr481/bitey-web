from __future__ import annotations

import re
from typing import Any

TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
ESSENTIAL_KEYS = ("user_query", "current_message", "goals", "constraints")
ORDER = ESSENTIAL_KEYS + ("conversation", "memory", "learned_cognitive_context", "evidence", "sources", "tools", "module_routing")
CAPABILITIES = frozenset({"general", "enterprise", "jobia", "sbt"})
CAPABILITY_KEYS = ("capability", "routing", "x-bitey-capability")
SPECIALIZED_KEYS = frozenset({"enterprise", "sbt", "jobia", "trading", "jobia_context", "enterprise_context", "sbt_context"})


def _string(value: Any, _seen: set[int] | None = None, _depth: int = 0) -> str:
    """Safely stringify context values without recursing forever on cyclic data."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if _depth > 20:
        return "[nested context truncated]"

    if _seen is None:
        _seen = set()

    if isinstance(value, (dict, list, tuple, set)):
        object_id = id(value)
        if object_id in _seen:
            return "[cyclic context omitted]"
        _seen.add(object_id)
        try:
            if isinstance(value, dict):
                return " ".join(
                    f"{k}: {_string(v, _seen, _depth + 1)}"
                    for k, v in value.items()
                ).strip()
            return " | ".join(
                item
                for item in (_string(v, _seen, _depth + 1) for v in value)
                if item
            ).strip()
        finally:
            _seen.remove(object_id)

    return str(value).strip()


def tokens(value: Any) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(_string(value)) if len(t) > 2}


def _items(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [f"{k}: {_string(v)}" for k, v in value.items()]
    if isinstance(value, (list, tuple, set)):
        return [item for item in (_string(v) for v in value) if item]
    text = _string(value)
    return [text] if text else []


def _normalize_capability(value: Any) -> str | None:
    candidate = str(value or "").strip().lower()
    return candidate if candidate in CAPABILITIES else None


def _target_capability(source: dict[str, Any], capability: str | None = None) -> str:
    """Prefer the server execution capability over arbitrary context metadata."""
    explicit = _normalize_capability(capability)
    if explicit:
        return explicit

    execution = source.get("execution_context") or source.get("execution")
    if isinstance(execution, dict):
        value = _normalize_capability(execution.get("capability"))
        if value:
            return value
        module = _normalize_capability(execution.get("module_id"))
        if module == "bitefixes":
            return "general"
        if module:
            return module

    return _normalize_capability(source.get("capability")) or "general"


def _tagged_capability(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in CAPABILITY_KEYS:
        capability = _normalize_capability(value.get(key))
        if capability:
            return capability
    return None


def _scope_value(value: Any, target: str, *, key: str | None = None) -> Any:
    """Remove explicitly foreign capability data while preserving untagged general context."""
    tagged = _tagged_capability(value)
    if tagged is not None and tagged != target:
        return None

    if isinstance(value, dict):
        # A specialized top-level block is scoped even when its internal records
        # predate capability tagging. This prevents token overlap from selecting it.
        normalized_key = str(key or "").strip().lower()
        if normalized_key in SPECIALIZED_KEYS:
            inferred = normalized_key.split("_", 1)[0]
            if inferred in CAPABILITIES and inferred != target:
                return None

        out: dict[str, Any] = {}
        for child_key, child_value in value.items():
            scoped = _scope_value(child_value, target, key=str(child_key))
            if scoped is not None:
                out[child_key] = scoped
        return out

    if isinstance(value, (list, tuple, set)):
        filtered = []
        for child in value:
            scoped = _scope_value(child, target)
            if scoped is not None:
                filtered.append(scoped)
        return type(value)(filtered) if not isinstance(value, tuple) else tuple(filtered)

    return value


def _scope_context(source: dict[str, Any], target: str) -> dict[str, Any]:
    scoped: dict[str, Any] = {}
    for key, value in source.items():
        if key.startswith("_"):
            continue
        scoped_value = _scope_value(value, target, key=key)
        if scoped_value is not None:
            scoped[key] = scoped_value
    return scoped


def select_context(source: dict[str, Any], capability: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    target = _target_capability(source, capability)
    scoped_source = _scope_context(source, target)
    query_tokens = tokens(scoped_source.get("user_query") or scoped_source.get("current_message"))
    selected: dict[str, Any] = {}
    scores: dict[str, float] = {}
    for key in ORDER:
        if key not in scoped_source or not _string(scoped_source[key]):
            continue
        overlap = len(query_tokens & tokens(scoped_source[key]))
        scores[key] = (1000.0 if key in ESSENTIAL_KEYS else 100.0) + overlap * 25
        selected[key] = scoped_source[key]
    for key, value in scoped_source.items():
        if key.startswith("_") or key in selected or not _string(value):
            continue
        overlap = len(query_tokens & tokens(value))
        if overlap:
            scores[key] = 50.0 + overlap * 20
            selected[key] = value
    return selected, {
        "scores": scores,
        "query_tokens": sorted(query_tokens),
        "capability": target,
    }


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
