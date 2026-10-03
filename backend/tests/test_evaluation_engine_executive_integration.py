import unittest

from app.core.bitey_brain import BiteyBrain
from app.core.cognitive_model import CognitiveModel
from app.core.evaluation_engine import EvaluationEngine


class EvaluationEngineExecutiveIntegrationTests(unittest.TestCase):
    def test_executive_contract_is_present_in_runtime_evaluation(self):
        message = "Investiga las opciones actuales para una API gratuita"
        context = {}
        cognition = CognitiveModel().process(message, context, evidence_available=True)
        context["cognition"] = cognition.as_dict()
        brain_state = BiteyBrain().think(message, {**context, "evidence_available": True})
        context["bitey_brain"] = brain_state.as_dict()
        context["selected_tools"] = list(brain_state.tool_priority)
        result = EvaluationEngine().evaluate(
            user_message=message,
            answer="He contrastado las opciones con evidencia disponible y separo los hechos de las inferencias. [S1] [S2]",
            context=context,
            evidence="SOURCE 1: https://docs.example\nCONTENT: documentation for API options\n\nSOURCE 2: https://provider.example\nCONTENT: provider information about API options",
        )
        self.assertIn("executive", result.as_dict())
        self.assertTrue(result.executive["passed"])
        self.assertEqual(result.executive["decision"], "accept")


if __name__ == "__main__":
    unittest.main()
