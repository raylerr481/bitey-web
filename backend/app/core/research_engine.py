from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchPlan:
    required: bool
    query: str
    reasons: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)


class ResearchEngine:
    """Provider-neutral research planning layer.

    It decides whether research is needed; actual web providers are adapters
    and are intentionally not hard-coded into the supracerebro core.
    """

    def plan(self, message: str, context: dict[str, Any]) -> ResearchPlan:
        explicit = bool(context.get("research", {}).get("requested"))
        freshness_terms = ("latest", "today", "current", "actual", "precio", "price", "2026")
        needs_freshness = any(term in message.lower() for term in freshness_terms)
        required = explicit or needs_freshness
        reasons = []
        if explicit:
            reasons.append("research_requested")
        if needs_freshness:
            reasons.append("freshness_sensitive")
        return ResearchPlan(required=required, query=message, reasons=reasons)
