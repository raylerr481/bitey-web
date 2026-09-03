from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any


@dataclass(frozen=True)
class ContradictionReport:
    contradiction_detected: bool
    evidence_count: int
    domains: list[str]
    action: str
    confidence: float
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContradictionEngine:
    """Lightweight evidence consistency gate before answer generation."""

    NEGATIONS = re.compile(r"\b(no|not|never|sin|não|nao)\b", re.I)
    NUMBERS = re.compile(r"[-+]?\d+(?:[.,]\d+)?")

    def inspect(self, evidence: list[dict[str, Any]] | None = None) -> ContradictionReport:
        usable = [e for e in (evidence or []) if e.get("ok") and e.get("content")]
        if len(usable) < 2:
            return ContradictionReport(False, len(usable), [], "answer_or_search_more", 0.45, ["insufficient_independent_evidence"])
        numbers: dict[str, set[str]] = {}
        for item in usable:
            text = str(item.get("content") or "")
            for n in self.NUMBERS.findall(text):
                numbers.setdefault(n.replace(",", "."), set()).add(str(item.get("url") or ""))
        conflicting = [n for n, sources in numbers.items() if len(sources) > 1]
        # Numeric disagreement is a useful signal, not proof of contradiction.
        contradiction = bool(conflicting)
        action = "search_more" if contradiction else "answer"
        confidence = 0.72 if contradiction else min(0.92, 0.55 + 0.08 * len(usable))
        reasons = ["multiple_sources_available"]
        if conflicting: reasons.append("same_numeric_claim_has_multiple_source_values")
        return ContradictionReport(contradiction, len(usable), [], action, confidence, reasons)
