import unittest

from app.core.deep_research import DeepResearchPlan, Evidence
from app.core.multistep_research_runtime import MultiStepResearchRuntime


class FakeResearchEngine:
    def __init__(self, reasons=None):
        self.reasons = reasons if reasons is not None else ["research_intent"]
        self.calls = []

    def plan(self, query, context):
        return DeepResearchPlan(query=query, reasons=list(self.reasons), mode="multistep")

    async def fetch_single(self, plan):
        self.calls.append(plan.query)
        plan.evidence.append(Evidence(url=f"https://example.test/{len(self.calls)}", title="Test evidence", content=f"Evidence for {plan.query}", ok=True))
        return plan


class MultiStepResearchRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_research_intent_is_deterministic_and_does_not_call_engine(self):
        engine = FakeResearchEngine(reasons=[])
        result = await MultiStepResearchRuntime(engine).run("Hello", {})
        self.assertEqual(result.stopped_reason, "research_not_required")
        self.assertEqual(result.attempted_questions, [])
        self.assertEqual(engine.calls, [])

    async def test_subquestion_limit_is_global(self):
        engine = FakeResearchEngine()
        result = await MultiStepResearchRuntime(engine, max_subquestions=3, max_passes=5).run("Investigate this", {})
        self.assertEqual(len(result.attempted_questions), 3)
        self.assertEqual(len(engine.calls), 3)
        self.assertEqual(result.stopped_reason, "subquestion_limit")
        self.assertLessEqual(len(result.passes), 5)

    async def test_pass_limit_is_enforced(self):
        engine = FakeResearchEngine()
        result = await MultiStepResearchRuntime(engine, max_subquestions=10, max_passes=1).run("Investigate this", {})
        self.assertEqual(len(result.passes), 1)
        self.assertEqual(result.stopped_reason, "pass_limit")
        self.assertLessEqual(len(result.attempted_questions), 10)

    async def test_followups_are_bounded_and_evidence_is_aggregated(self):
        engine = FakeResearchEngine()
        result = await MultiStepResearchRuntime(engine, max_subquestions=4, max_passes=2).run("Investigate this", {})
        self.assertEqual(len(result.attempted_questions), 4)
        self.assertEqual(len(result.passes), 2)
        self.assertEqual(result.successful_sources, 4)
        self.assertTrue(result.evidence_context())
        self.assertEqual(result.as_dict()["max_subquestions"], 4)
        self.assertEqual(result.as_dict()["max_passes"], 2)

    def test_invalid_bounds_are_rejected(self):
        with self.assertRaises(ValueError):
            MultiStepResearchRuntime(max_subquestions=0)
        with self.assertRaises(ValueError):
            MultiStepResearchRuntime(max_passes=0)


if __name__ == "__main__":
    unittest.main()
