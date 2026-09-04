from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .bitey_brain import BiteyBrain
from .deep_research import DeepResearchEngine


@dataclass
class ResearchStep:
    index: int
    query: str
    status: str = "pending"
    sources: list[dict[str, Any]] = field(default_factory=list)
    evidence: str = ""


@dataclass
class MultiStepResearchResult:
    original_query: str
    steps: list[ResearchStep]
    evidence_context: str
    decision: dict[str, Any]
    bounded: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "original_query": self.original_query,
            "steps": [step.__dict__ for step in self.steps],
            "evidence_context": self.evidence_context,
            "decision": self.decision,
            "bounded": self.bounded,
        }


class MultiStepResearchRuntime:
    """Bounded research executor owned by Bitey's cognitive control layer."""

    def __init__(self, max_steps: int = 4, max_sources_per_step: int = 5):
        self.max_steps = max(1, min(max_steps, 8))
        self.max_sources_per_step = max(1, min(max_sources_per_step, 8))
        self.brain = BiteyBrain()
        self.research = DeepResearchEngine()

    def _queries(self, query: str, decision: dict[str, Any]) -> list[str]:
        if decision.get("reasoning_mode") != "evidence_first" and decision.get("reasoning_mode") != "decompose_verify_synthesize":
            return [query]
        parts = [query]
        low = query.lower()
        if any(x in low for x in ("compara", "contrasta", "versus", "vs")):
            parts.append(f"evidencia independiente sobre: {query}")
        else:
            parts.append(f"fuentes oficiales y evidencia sobre: {query}")
            parts.append(f"perspectivas independientes y contradicciones sobre: {query}")
        return list(dict.fromkeys(parts))[: self.max_steps]

    async def run(self, query: str, context: dict[str, Any] | None = None) -> MultiStepResearchResult:
        ctx = dict(context or {})
        thought = self.brain.think(query, {**ctx, "research": True})
        decision = thought.as_dict()
        steps: list[ResearchStep] = []
        evidence_blocks: list[str] = []
        for index, step_query in enumerate(self._queries(query, decision), start=1):
            step = ResearchStep(index=index, query=step_query, status="running")
            plan = self.research.plan(step_query, {"research_mode": "deep"})
            plan = await self.research.fetch(plan)
            step.sources = self.research.source_summary(plan)[: self.max_sources_per_step]
            step.evidence = self.research.evidence_context(plan)
            step.status = "completed" if step.evidence else "no_evidence"
            steps.append(step)
            if step.evidence:
                evidence_blocks.append(f"STEP {index}\n{step.evidence}")
        return MultiStepResearchResult(
            original_query=query,
            steps=steps,
            evidence_context="\n\n".join(evidence_blocks),
            decision=decision,
        )

    def status(self) -> dict[str, Any]:
        return {
            "name": "MultiStepResearchRuntime",
            "enabled": True,
            "max_steps": self.max_steps,
            "max_sources_per_step": self.max_sources_per_step,
            "unbounded_execution": False,
        }
