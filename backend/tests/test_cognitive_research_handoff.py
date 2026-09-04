import unittest

from app.core.bitey_brain import BiteyBrain
from app.core.research_engine import ResearchEngine


class CognitiveResearchHandoffTests(unittest.TestCase):
    def test_policy_decision_is_handed_to_brain(self):
        context = {}
        plan = ResearchEngine().plan("Investiga la última versión de Python y cita fuentes", context)
        self.assertTrue(plan.required)
        self.assertEqual(context["research"]["owner"], "bitey_research_policy")
        self.assertEqual(context["research"]["strategy"], "multi_source_research")

        state = BiteyBrain().think("Investiga la última versión de Python y cita fuentes", context)
        self.assertTrue(state.evidence_required)
        self.assertEqual(state.reasoning_mode, "evidence_first")
        self.assertIn("web_research", state.tool_priority)

    def test_policy_can_explicitly_disable_research_for_ordinary_request(self):
        context = {}
        plan = ResearchEngine().plan("Explícame qué es una variable en Python", context)
        self.assertFalse(plan.required)
        self.assertEqual(context["research"]["owner"], "bitey_research_policy")
        state = BiteyBrain().think("Explícame qué es una variable en Python", context)
        self.assertFalse(state.evidence_required)
        self.assertNotIn("web_research", state.tool_priority)


if __name__ == "__main__":
    unittest.main()
