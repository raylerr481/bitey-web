"""Conversational intent helpers for Bitey IA Web.

This module keeps simple conversational turns out of the factual-evidence
fallback. Greetings and other low-risk social turns should be answered
conversationally rather than treated as unsupported factual claims.
"""

from __future__ import annotations

import re
from typing import Optional


_GREETING_PATTERNS = (
    r"^(?:hola|holaa+|hello|hi|hey|buenas|buenos días|buenos dias|buen día|buen dia|buenas tardes|buenas noches)[!.?, ]*$",
)

_FAREWELL_PATTERNS = (
    r"^(?:adiós|adios|chao|chau|hasta luego|nos vemos|bye)[!.?, ]*$",
)

_THANKS_PATTERNS = (
    r"^(?:gracias|muchas gracias|thank you|thanks)[!.?, ]*$",
)



def classify_conversational_intent(text: str) -> Optional[str]:
    """Return a safe conversational intent before factual routing.

    Only very high-confidence, low-risk social turns are intercepted here.
    All other text continues through the normal cognitive/factual pipeline.
    """
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    for pattern in _GREETING_PATTERNS:
        if re.fullmatch(pattern, normalized):
            return "greeting"
    for pattern in _FAREWELL_PATTERNS:
        if re.fullmatch(pattern, normalized):
            return "farewell"
    for pattern in _THANKS_PATTERNS:
        if re.fullmatch(pattern, normalized):
            return "thanks"
    return None



def conversational_response(intent: str) -> str:
    """Generate deterministic responses for basic social turns."""
    responses = {
        "greeting": "¡Hola! 👋 Soy Bitey IA. Estoy aquí para ayudarte. ¿Qué quieres hacer?",
        "farewell": "¡Hasta luego! 👋 Cuando quieras, seguimos.",
        "thanks": "¡De nada! 😊 Estoy aquí para ayudarte.",
    }
    return responses[intent]
