from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvidenceSource:
    type: str
    locator: str = ""
    title: str = ""
    excerpt: str = ""
    independent_group: str = ""
    supports: bool = True


@dataclass
class KnowledgeClaim:
    claim: str
    sources: list[EvidenceSource] = field(default_factory=list)
    conflicts: int = 0

    def independent_groups(self) -> set[str]:
        return {s.independent_group or s.type for s in self.sources if s.supports}

    def has_conflict(self) -> bool:
        return self.conflicts > 0 or any(not s.supports for s in self.sources)


class EvidenceEngine:
    """Deterministic evidence scoring copied from the proven diagnostic pattern."""
    def score(self, hypotheses: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored = []
        for hypothesis in hypotheses:
            item = dict(hypothesis)
            name = str(item.get("name", "")).lower()
            support = sum(1 for ev in evidence if str(ev.get("supports", "")).lower() == name)
            contradiction = sum(1 for ev in evidence if str(ev.get("contradicts", "")).lower() == name)
            item["evidence_score"] = max(0, support - contradiction)
            scored.append(item)
        return sorted(scored, key=lambda x: (x.get("evidence_score", 0), x.get("confidence", 0)), reverse=True)


class HypothesisEngine:
    """Maintains competing hypotheses without asking an LLM to choose blindly."""
    def rank(self, hypotheses: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ranked = []
        for hypothesis in hypotheses:
            item = dict(hypothesis)
            score = float(item.get("confidence", 0.0) or 0.0)
            name = str(item.get("name", ""))
            for ev in evidence:
                if str(ev.get("supports", "")) == name:
                    score += 0.15
                elif str(ev.get("contradicts", "")) == name:
                    score -= 0.20
            item["confidence"] = max(0.0, min(1.0, score))
            ranked.append(item)
        return sorted(ranked, key=lambda x: x["confidence"], reverse=True)

    @staticmethod
    def record_result(evidence: list[dict[str, Any]], hypothesis: str, success: bool, observation: str) -> list[dict[str, Any]]:
        evidence.append({"source": "verification", "observation": observation, "supports": hypothesis if success else None, "contradicts": None if success else hypothesis, "result": "success" if success else "failure"})
        return evidence


def compare_candidates(*, query: str, candidates: list[dict[str, Any]], core_confidence: float = 0.0) -> dict[str, Any]:
    """General answer comparison; no enterprise authority is embedded."""
    q = {w.lower() for w in query.split() if len(w) > 2}
    ranked = []
    for candidate in candidates:
        answer = str(candidate.get("answer") or "")
        words = {w.lower() for w in answer.split() if len(w) > 2}
        relevance = len(q & words) / max(1, len(q))
        evidence = min(1.0, float(candidate.get("evidence_score", 0.0) or 0.0))
        safety = min(1.0, max(0.0, float(candidate.get("safety", 1.0) or 0.0)))
        score = 0.45 * relevance + 0.30 * evidence + 0.15 * safety + 0.10 * max(0.0, min(1.0, core_confidence))
        ranked.append({**candidate, "score": round(score, 4)})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    selected = ranked[0] if ranked else None
    return {"status": "compared" if selected else "no_candidates", "selected": selected, "ranked": ranked, "confidence": selected["score"] if selected else 0.0}
