"""Generic multi-turn conversation context extraction.

This module tracks continuity signals only. It is deliberately not an evidence
source: remembered context may guide interpretation, but current/fresh claims
still require the normal evidence pipeline.
"""

from __future__ import annotations

import re
from typing import Any


_REFERENCE_WORDS = {
    "esto", "eso", "ello", "esa", "ese", "aquello", "aquel", "aquella",
    "este", "esta", "estos", "estas", "allí", "alli", "ahí", "ahi",
    "anterior", "siguiente", "segundo", "segunda", "primero", "primera",
    "opción", "opcion", "otro", "otra", "mismo", "misma", "lo", "la",
    "el", "ellos", "ellas",
}
_CONNECTORS = {"y", "e", "and", "then", "então", "entao", "también", "tambien"}
_TIME_WORDS = {
    "hoy", "ahora", "actual", "actualmente", "mañana", "ayer", "anoche",
    "antes", "después", "despues", "luego", "próximo", "proximo", "último",
    "ultimo", "semana", "mes", "año", "ano", "today", "tomorrow", "yesterday",
    "now", "later", "next", "previous",
}
_TOPIC_HINTS = (
    ("weather", ("clima", "tiempo", "temperatura", "weather", "forecast", "previsión", "previsão")),
    ("finance", ("bitcoin", "ethereum", "btc", "eth", "acciones", "precio", "mercado", "stock")),
    ("programming", ("código", "codigo", "python", "javascript", "typescript", "api", "bug", "error")),
    ("research", ("investiga", "investigar", "busca", "fuentes", "investigación", "research")),
    ("comparison", ("comparar", "comparación", "mejor", "mejor opción", "diferencia", "versus", "vs")),
    ("shopping", ("comprar", "compra", "producto", "precio", "tienda", "oferta")),
    ("travel", ("viaje", "hotel", "vuelo", "turismo", "viajar")),
    ("trading", ("trading", "forex", "mt4", "mt5", "eurusd", "btc/usd")),
)


def _clean(value: Any, limit: int = 1200) -> str:
    return " ".join(str(value or "").split())[:limit]


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-záéíóúüñ0-9]{3,}", value.casefold())


def _topic(text: str) -> str | None:
    normalized = text.casefold()
    for topic, hints in _TOPIC_HINTS:
        if any(hint in normalized for hint in hints):
            return topic
    return None


def _extract_entities(text: str) -> list[str]:
    # Conservative entity continuity: capitalized multi-word names, URLs,
    # tickers/technical identifiers, and explicit "en/de X" location phrases.
    found: list[str] = []
    for match in re.findall(r"https?://[^\s<>()]+", text):
        found.append(match.rstrip(".,;"))
    for match in re.findall(r"\b(?:[A-ZÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑ-]+(?:\s+[A-ZÁÉÍÓÚÜÑ][\wÁÉÍÓÚÜÑ-]+){0,3})\b", text):
        if len(match) > 2 and match not in found:
            found.append(match)
    for match in re.findall(r"\b[A-Z]{2,6}(?:/[A-Z]{2,6})?\b", text):
        if match not in found:
            found.append(match)
    for match in re.findall(r"\b(?:en|em|in|de|from|para|to)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][\wÁÉÍÓÚÜÑáéíóúüñ-]*(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][\wÁÉÍÓÚÜÑáéíóúüñ-]*){0,2})", text, re.I):
        value = _clean(match, 120)
        if value and value.casefold() not in {"el", "la", "los", "las", "un", "una"} and value not in found:
            found.append(value)
    return found[:12]


def build_conversation_context(
    history: list[dict[str, Any]],
    current_query: str,
    *,
    active_state: dict[str, Any] | None = None,
    limit: int = 6,
) -> dict[str, Any]:
    """Build generic continuity state while keeping evidence trust boundaries explicit."""
    users = [_clean(item.get("content")) for item in history if item.get("role") == "user" and item.get("content")]
    assistants = [_clean(item.get("content"), 1800) for item in history if item.get("role") == "assistant" and item.get("content")]
    prior_user = users[-1] if users else ""
    prior_answer = assistants[-1] if assistants else ""
    text = _clean(current_query)
    tokens = set(_tokens(text))
    reference_tokens = sorted(tokens.intersection(_REFERENCE_WORDS))
    connector = bool(re.match(r"^(?:y|e|and|then|então|entao|también|tambien)\b", text, re.I))
    temporal = sorted(tokens.intersection(_TIME_WORDS))
    current_topic = _topic(text)
    prior_topic = _topic(prior_user) or _topic(prior_answer)
    entities = _extract_entities(text)
    prior_entities = _extract_entities(prior_user)
    continuity_signal = bool(
        prior_user
        and (
            connector
            or reference_tokens
            or temporal
            or not current_topic
            or bool(active_state and active_state.get("current_goal"))
        )
    )

    previous_result = {}
    for item in reversed(history):
        if item.get("role") != "assistant":
            continue
        metadata = item.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("reference_context"), dict):
            previous_result = metadata["reference_context"]
            break

    return {
        "topic": current_topic or prior_topic,
        "topic_source": "current_request" if current_topic else ("prior_turn" if prior_topic else "unknown"),
        "continuation": continuity_signal,
        "connector": connector,
        "references": reference_tokens[:8],
        "temporal_context": temporal[:8],
        "entities": entities[:12] or prior_entities[:12],
        "current_entities": entities[:12],
        "prior_entities": prior_entities[:12],
        "last_user_request": prior_user[:1000],
        "last_assistant_answer": prior_answer[:1800],
        "previous_result_context": previous_result,
        "recent_turns": [
            {
                "role": str(item.get("role") or ""),
                "content": _clean(item.get("content"), 900),
            }
            for item in history[-max(2, limit * 2):]
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ],
        "priority": "current_request_then_explicit_active_state_then_recent_context",
        "trust": "continuity_only_not_evidence",
        "evidence_source": False,
    }
