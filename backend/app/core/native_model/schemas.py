from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_CAPABILITIES = frozenset({
    "web_research", "weather", "workspace_files", "calculator", "code_reasoning",
})

@dataclass(frozen=True)
class NativePlan:
    intent: str
    domain: str
    capabilities: tuple[str, ...]
    external_information_required: bool
    freshness_required: bool
    verification_required: bool
    search_objective: str
    confidence: float
    reasons: tuple[str, ...]
    query_strategy: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "NativePlan":
        caps = tuple(dict.fromkeys(str(x) for x in (raw.get("capabilities") or []) if str(x) in ALLOWED_CAPABILITIES))
        confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.0))))
        return cls(
            intent=str(raw.get("intent") or "answer_or_assist")[:120],
            domain=str(raw.get("domain") or "general")[:120],
            capabilities=caps,
            external_information_required=bool(raw.get("external_information_required")),
            freshness_required=bool(raw.get("freshness_required")),
            verification_required=bool(raw.get("verification_required")),
            search_objective=str(raw.get("search_objective") or "answer the user's goal")[:1000],
            confidence=confidence,
            reasons=tuple(str(x)[:200] for x in (raw.get("reasons") or [])[:12]),
            query_strategy=tuple(str(x)[:120] for x in (raw.get("query_strategy") or [])[:12]),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent, "domain": self.domain, "capabilities": list(self.capabilities),
            "external_information_required": self.external_information_required,
            "freshness_required": self.freshness_required, "verification_required": self.verification_required,
            "search_objective": self.search_objective, "confidence": self.confidence,
            "reasons": list(self.reasons), "query_strategy": list(self.query_strategy),
        }
