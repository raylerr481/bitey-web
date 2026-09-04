"""Bounded multi-step research orchestration for Bitey Brain."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

Researcher = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class MultiStepResearchResult:
    evidence: list[dict[str, Any]] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    passes: int = 0
    stopped_early: bool = False
    stop_reason: str = "max_passes"

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence,
            "queries": self.queries,
            "passes": self.passes,
            "stopped_early": self.stopped_early,
            "stop_reason": self.stop_reason,
            "source_count": len(self.evidence),
        }


class MultiStepResearchRuntime:
    """Executes research as a bounded tool, never as an autonomous LLM loop."""

    def __init__(self, researcher: Researcher, *, max_subquestions: int = 3, max_passes: int = 2, max_sources: int = 8) -> None:
        self.researcher = researcher
        self.max_subquestions = max(1, max_subquestions)
        self.max_passes = max(1, max_passes)
        self.max_sources = max(1, max_sources)

    async def run(self, query: str, context: dict[str, Any] | None = None, subquestions: list[str] | None = None) -> MultiStepResearchResult:
        ctx = dict(context or {})
        candidates = [query, *(subquestions or [])]
        queries: list[str] = []
        seen: set[str] = set()
        evidence: list[dict[str, Any]] = []
        result = MultiStepResearchResult()

        for current_pass in range(self.max_passes):
            result.passes = current_pass + 1
            for candidate in candidates[: self.max_subquestions]:
                normalized = " ".join(candidate.lower().split())
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                queries.append(candidate)
                payload = await self.researcher(candidate, {**ctx, "research_pass": current_pass + 1, "research_queries": list(queries)})
                for item in payload.get("evidence", []) if isinstance(payload, dict) else []:
                    if not isinstance(item, dict):
                        continue
                    key = str(item.get("url") or item.get("id") or item.get("content") or "").strip()
                    if key and key not in {str(x.get("url") or x.get("id") or x.get("content") or "").strip() for x in evidence}:
                        evidence.append(item)
                    if len(evidence) >= self.max_sources:
                        result.stopped_early = True
                        result.stop_reason = "max_sources"
                        result.evidence = evidence[: self.max_sources]
                        result.queries = queries
                        return result
                if self._sufficient(payload, evidence):
                    result.stopped_early = True
                    result.stop_reason = "evidence_sufficient"
                    result.evidence = evidence
                    result.queries = queries
                    return result
            # No implicit unlimited planning: the caller must supply follow-up questions.
            break

        result.evidence = evidence[: self.max_sources]
        result.queries = queries
        if result.passes >= self.max_passes:
            result.stop_reason = "max_passes"
        elif not evidence:
            result.stop_reason = "no_evidence"
        else:
            result.stop_reason = "bounded_completion"
        return result

    @staticmethod
    def _sufficient(payload: dict[str, Any], evidence: list[dict[str, Any]]) -> bool:
        if not isinstance(payload, dict):
            return False
        if payload.get("sufficient") is True:
            return True
        return len(evidence) >= int(payload.get("minimum_evidence", 2))
