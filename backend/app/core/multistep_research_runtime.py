from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .deep_research import DeepResearchEngine, DeepResearchPlan


@dataclass
class ResearchPass:
    number: int
    questions: list[str] = field(default_factory=list)
    completed: int = 0
    successful: int = 0


@dataclass
class MultiStepResearchResult:
    query: str
    attempted_questions: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    passes: list[ResearchPass] = field(default_factory=list)
    stopped_reason: str = "not_started"
    max_subquestions: int = 4
    max_passes: int = 2

    @property
    def successful_sources(self) -> int:
        return sum(1 for item in self.evidence if item.get("ok"))

    @property
    def confidence(self) -> float:
        if not self.attempted_questions:
            return 0.0
        successful_questions = sum(1 for item in self.passes for _ in range(item.successful))
        return round(min(0.95, 0.30 + 0.65 * (successful_questions / len(self.attempted_questions))), 3)

    def evidence_context(self) -> str:
        chunks: list[str] = []
        for index, item in enumerate(self.evidence, 1):
            if not item.get("ok") or not item.get("content"):
                continue
            chunks.append(
                f"SOURCE {index}: {item.get('url', '')}\n"
                f"TITLE: {item.get('title', '')}\n"
                f"EVIDENCE:\n{item.get('content', '')}"
            )
        return "\n\n".join(chunks)

    def source_summary(self) -> list[dict[str, Any]]:
        return [
            {
                "url": item.get("url"),
                "title": item.get("title", ""),
                "ok": bool(item.get("ok")),
                "error": item.get("error"),
            }
            for item in self.evidence
        ]

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "attempted_questions": list(self.attempted_questions),
            "passes": [
                {
                    "number": item.number,
                    "questions": list(item.questions),
                    "completed": item.completed,
                    "successful": item.successful,
                }
                for item in self.passes
            ],
            "source_count": len(self.evidence),
            "successful_sources": self.successful_sources,
            "confidence": self.confidence,
            "stopped_reason": self.stopped_reason,
            "max_subquestions": self.max_subquestions,
            "max_passes": self.max_passes,
        }


class MultiStepResearchRuntime:
    """Bounded research orchestration owned by Bitey, not by a model.

    The runtime decides how many research questions and passes may execute.
    DeepResearchEngine remains a capability provider for public-web evidence.
    No model is required to create the initial subquestions, which keeps the
    safety and economic bounds deterministic.
    """

    def __init__(
        self,
        engine: DeepResearchEngine | None = None,
        *,
        max_subquestions: int = 4,
        max_passes: int = 2,
    ) -> None:
        if max_subquestions < 1:
            raise ValueError("max_subquestions must be >= 1")
        if max_passes < 1:
            raise ValueError("max_passes must be >= 1")
        self.engine = engine or DeepResearchEngine()
        self.max_subquestions = max_subquestions
        self.max_passes = max_passes

    async def run(self, query: str, context: dict[str, Any] | None = None) -> MultiStepResearchResult:
        ctx = dict(context or {})
        initial = self.engine.plan(query, ctx)
        result = MultiStepResearchResult(
            query=query,
            max_subquestions=self.max_subquestions,
            max_passes=self.max_passes,
        )

        if not initial.reasons:
            result.stopped_reason = "research_not_required"
            return result

        questions = self._initial_questions(query, initial)
        seen: set[str] = set()

        for pass_number in range(1, self.max_passes + 1):
            available = [q for q in questions if q.strip() and q.strip().lower() not in seen]
            remaining = self.max_subquestions - len(result.attempted_questions)
            if remaining <= 0 or not available:
                result.stopped_reason = "subquestion_limit" if remaining <= 0 else "no_new_questions"
                break

            current = available[:remaining]
            research_pass = ResearchPass(number=pass_number, questions=current)
            result.passes.append(research_pass)

            for question in current:
                normalized = question.strip().lower()
                seen.add(normalized)
                result.attempted_questions.append(question)
                plan = DeepResearchPlan(
                    query=question,
                    mode=initial.mode,
                    reasons=list(initial.reasons),
                )
                fetched = await self.engine.fetch(plan)
                usable = 0
                for evidence in fetched.evidence:
                    payload = {
                        "url": evidence.url,
                        "title": evidence.title,
                        "content": evidence.content,
                        "ok": evidence.ok,
                        "error": evidence.error,
                        "question": question,
                        "pass": pass_number,
                    }
                    result.evidence.append(payload)
                    usable += int(evidence.ok and bool(evidence.content))
                research_pass.completed += 1
                if usable:
                    research_pass.successful += 1

            if pass_number >= self.max_passes:
                result.stopped_reason = "pass_limit"
                break

            questions = self._follow_up_questions(query, result)
            if not questions:
                result.stopped_reason = "evidence_sufficient_or_no_followups"
                break

        if not result.stopped_reason or result.stopped_reason == "not_started":
            result.stopped_reason = "completed"
        return result

    @staticmethod
    def _initial_questions(query: str, plan: DeepResearchPlan) -> list[str]:
        questions = [query]
        reasons = set(plan.reasons)
        if "freshness" in reasons or "research_intent" in reasons:
            questions.append(f"What current evidence supports this question: {query}")
        if "research_intent" in reasons:
            questions.append(f"What reliable evidence could contradict or limit the answer to: {query}")
        if plan.urls:
            questions.append(f"What do the supplied sources establish about: {query}")
        return questions

    @staticmethod
    def _follow_up_questions(query: str, result: MultiStepResearchResult) -> list[str]:
        if result.successful_sources == 0:
            return []
        return [
            f"What important limitations or uncertainty remain after researching: {query}",
            f"What evidence should be cross-checked before concluding: {query}",
        ]
