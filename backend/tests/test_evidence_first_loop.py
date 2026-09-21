import unittest

from app.core.bitey_brain import BiteyBrain
from app.core.evaluation_engine import EvaluationEngine
from app.core.tool_orchestrator import ToolOrchestrator


class EvidenceFirstLoopTests(unittest.TestCase):
    def setUp(self):
        self.orchestrator = ToolOrchestrator()
        self.brain = BiteyBrain()

    def test_substantive_general_question_selects_web_search(self):
        context = {}
        result = self.orchestrator.cognitive_selection("¿Qué es blockchain?", context)
        self.assertIn("search", result["selected_tools"])
        self.assertTrue(result["brain"]["evidence_required"])

    def test_greeting_does_not_select_web_search(self):
        context = {}
        result = self.orchestrator.cognitive_selection("Hola", context)
        self.assertNotIn("search", result["selected_tools"])
        self.assertFalse(result["brain"]["evidence_required"])

    def test_identity_request_does_not_select_web_search(self):
        context = {}
        result = self.orchestrator.cognitive_selection("¿Quién eres?", context)
        self.assertNotIn("search", result["selected_tools"])
        self.assertFalse(result["brain"]["evidence_required"])

    def test_research_failure_requires_revision_when_answer_claims_facts(self):
        context = {
            "evidence_required": True,
            "cognition": {
                "intention": {"intent": "answer_or_assist", "domain": "general"}
            },
        }
        result = EvaluationEngine().evaluate(
            user_message="¿Qué es una institución desconocida?",
            answer="Es una organización internacional muy importante.",
            context=context,
            evidence="",
        )
        self.assertEqual(result.decision, "revise")
        self.assertIn("evidence_required_but_unavailable", result.reasons)
        self.assertIn("missing_evidence_disclosure", result.reasons)


if __name__ == "__main__":
    unittest.main()
