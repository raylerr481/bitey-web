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
    ("programming", ("código", "codigo", "python", "javascript", "typescript", "api", "bug", "error", "docker")),
    ("research", ("investiga", "investigar", "busca", "fuentes", "investigación", "research")),
    ("comparison", ("comparar", "compara", "comparando", "comparación", "comparativo", "mejor", "mejor opción", "diferencia", "versus", "vs")),
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
    # Comparison is a semantic task that should outrank a preceding
    # research verb (for example: "investiga ... y compara ...").
    comparison_hints = dict(_TOPIC_HINTS)["comparison"]
    if any(hint in normalized for hint in comparison_hints):
        return "comparison"
    for topic, hints in _TOPIC_HINTS:
        if topic == "comparison":
            continue
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



def _reference_resolution(
    *,
    text: str,
    references: list[str],
    current_entities: list[str],
    recent_entities: list[str],
    prior_user: str,
    prior_answer: str,
    previous_result: dict[str, Any],
) -> dict[str, Any]:
    """Resolve conversational references without promoting memory to evidence.

    The resolver only identifies likely referents. It never asserts that the
    referenced object is true, current, or authoritative.
    """
    normalized = text.casefold()
    options = previous_result.get("options") if isinstance(previous_result, dict) else None
    candidates: list[dict[str, Any]] = []
    target: dict[str, Any] | None = None

    ordinal_map = {
        "primero": 0, "primera": 0,
        "segundo": 1, "segunda": 1,
        "tercero": 2, "tercera": 2,
        "cuarto": 3, "cuarta": 3,
        "quinto": 4, "quinta": 4,
    }
    ordinal = next((word for word in ordinal_map if re.search(rf"\b{re.escape(word)}\b", normalized)), None)
    if ordinal and isinstance(options, list):
        index = ordinal_map[ordinal]
        if index < len(options):
            value = options[index]
            target = {
                "kind": "previous_result_option",
                "index": index + 1,
                "value": _clean(value, 500),
                "source": "previous_result_context",
            }
            candidates.append(target)

    # A demonstrative/pronominal reference points to the nearest conversational
    # object, but the answer text remains only context, never evidence.
    if target is None and references:
        if any(word in references for word in ("esto", "eso", "ello", "aquello", "esa", "ese", "este", "esta", "lo", "la")):
            referent = current_entities[-1:] or recent_entities[-1:]
            target = {
                "kind": "recent_entity" if referent else "previous_turn",
                "value": referent[0] if referent else (prior_user or prior_answer)[:500],
                "source": "conversation_context",
            }
            candidates.append(target)

    if target is None and references and ("anterior" in references or "previo" in references):
        target = {
            "kind": "previous_turn",
            "value": prior_user[:500] or prior_answer[:500],
            "source": "conversation_context",
        }
        candidates.append(target)

    if target is None and references and ("otro" in references or "otra" in references):
        candidates.append({
            "kind": "contrast_with_recent",
            "value": recent_entities[-1] if recent_entities else "",
            "source": "conversation_context",
        })

    confidence = "high" if target and target.get("kind") == "previous_result_option" else (
        "medium" if target else "low"
    )
    return {
        "resolved": bool(target),
        "target": target,
        "candidates": candidates[:4],
        "confidence": confidence,
        "uses_previous_result": bool(target and target.get("source") == "previous_result_context"),
        "trust": "continuity_only_not_evidence",
        "evidence_source": False,
    }

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
    connector = bool(re.match(r"^[¿?!.,\s]*(?:y|e|and|then|então|entao|también|tambien)\b", text, re.I))
    temporal = sorted(tokens.intersection(_TIME_WORDS))
    current_topic = _topic(text)
    prior_topic = _topic(prior_user) or _topic(prior_answer)
    # Search a short recent window for the last stable topic/entity signal. This
    # keeps continuity generic instead of making it dependent on one domain.
    recent_user_turns = users[-max(3, limit):]
    recent_topics = [topic for topic in (_topic(item) for item in recent_user_turns) if topic]
    recent_topic = recent_topics[-1] if recent_topics else prior_topic
    entities = _extract_entities(text)
    prior_entities = _extract_entities(prior_user)
    recent_entities: list[str] = []
    for item in reversed(recent_user_turns):
        for entity in _extract_entities(item):
            if entity.casefold() not in {value.casefold() for value in recent_entities}:
                recent_entities.append(entity)
            if len(recent_entities) >= 12:
                break
        if len(recent_entities) >= 12:
            break
    continuity_signal = bool(
        prior_user
        and (
            connector
            or reference_tokens
            or temporal
            or (current_topic is not None and current_topic == prior_topic)
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

    reference_resolution = _reference_resolution(
        text=text,
        references=reference_tokens[:8],
        current_entities=entities[:12],
        recent_entities=recent_entities[:12],
        prior_user=prior_user,
        prior_answer=prior_answer,
        previous_result=previous_result,
    )

    return {
        "topic": current_topic or recent_topic,
        "topic_source": "current_request" if current_topic else ("recent_turns" if recent_topic else "unknown"),
        "topic_history": list(dict.fromkeys(recent_topics))[-4:],
        "continuation": continuity_signal,
        "continuity_confidence": (
            "high" if (connector and (prior_user or recent_entities)) or (reference_tokens and recent_entities)
            else "medium" if continuity_signal
            else "low"
        ),
        "connector": connector,
        "references": reference_tokens[:8],
        "temporal_context": temporal[:8],
        "entities": entities[:12] or recent_entities[:12] or prior_entities[:12],
        "current_entities": entities[:12],
        "prior_entities": prior_entities[:12],
        "recent_entities": recent_entities[:12],
        "entity_continuity": bool(entities or prior_entities or recent_entities),
        "last_user_request": prior_user[:1000],
        "last_assistant_answer": prior_answer[:1800],
        "previous_result_context": previous_result,
        "reference_resolution": reference_resolution,
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
