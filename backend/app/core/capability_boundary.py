from __future__ import annotations

import re


_ENTERPRISE_KEYWORDS = re.compile(
    r"\b(?:bitey\s*enterprise|bitey\s*empresarial|marketing empresarial|marketing digital|"
    r"ventas|lead generation|generación de leads|seo|crm|campañas|"
    r"automatización comercial|automatizacion comercial)\b",
    re.IGNORECASE,
)


def classify_server_capability(message: str) -> str:
    """Classify only the capability needed for server-side context isolation.

    Enterprise is selected from the current message, never from client metadata.
    Other capabilities remain general here and are handled by their existing
    routing layers.
    """
    return "enterprise" if _ENTERPRISE_KEYWORDS.search(str(message or "")) else "general"
