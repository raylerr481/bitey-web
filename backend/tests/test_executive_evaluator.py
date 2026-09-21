import unittest

from app.core.bitey_brain import BiteyBrain
from app.core.cognitive_model import CognitiveModel
from app.core.executive_evaluator import ExecutiveEvaluator


def decision(message: str, context: dict | None = None):
    ctx = dict(context or {})
    cognition = CognitiveModel().process(message, ctx, evidence_available=bool(ctx.get("evidence_available")))
    ctx["cognition"] = cognition.as_dict()
    return BiteyBrain().think(message, ctx)


class ExecutiveEvaluatorContractTests(unittest.TestCase):
    def test_research_without_evidence_is_rejected(self):
        state = decision("Investiga las opciones actuales para una API gratuita")
        result = ExecutiveEvaluator().evaluate(state=state, answer="Esta es una respuesta sin fuentes verificables.", evidence="", selected_tools=[])
        self.assertFalse(result.passed)
        self.assertEqual(result.decision, "revise")
        self.assertFalse(result.evidence_compliant)

    def test_weather_requires_weather_tool(self):
        state = decision("¿Qué temperatura hace ahora en Esteio?")
        result = ExecutiveEvaluator().evaluate(state=state, answer="La temperatura actual es la consultada mediante datos meteorológicos verificables.", evidence="Open-Meteo current weather", selected_tools=[])
        self.assertFalse(result.tool_compliant)
        self.assertFalse(result.passed)
        self.assertIn("required_tool_not_executed", result.reasons)

    def test_compliant_output_is_accepted(self):
        state = decision("Investiga las opciones actuales para una API gratuita")
        result = ExecutiveEvaluator().evaluate(state=state, answer="He comparado las opciones con evidencia verificable antes de presentar esta conclusión. [S1]", evidence="SOURCE 1: https://example.org\nCONTENT: evidencia verificable sobre las opciones.", selected_tools=["search"])
        self.assertTrue(result.passed)
        self.assertEqual(result.decision, "accept")
        self.assertTrue(result.evidence_compliant)
        self.assertTrue(result.tool_compliant)
        self.assertTrue(result.provider_independent)

    def test_trading_cannot_become_live_execution(self):
        state = decision("Compra EURUSD con dinero real")
        result = ExecutiveEvaluator().evaluate(state=state, answer="No se ejecutará ninguna operación real; la ejecución está bloqueada por la política de riesgo.", evidence="", selected_tools=[])
        self.assertTrue(result.risk_compliant)
        self.assertTrue(result.passed)


    def test_general_answer_with_sbt_drift_is_rejected_for_revision(self):
        state = decision("¿Qué es Bitcoin?")
        result = ExecutiveEvaluator().evaluate(
            state=state,
            answer="Bitcoin es un activo que aquí analizaremos con SBT y señales de trading.",
            evidence="SOURCE 1: https://example.org\nCONTENT: Bitcoin is a digital asset.",
            selected_tools=["search"],
        )
        self.assertFalse(result.passed)
        self.assertIn("general_domain_specialized_module_drift", result.reasons)

    def test_research_answer_requires_valid_source_reference(self):
        state = decision("¿Qué es Bitcoin?")
        evidence = "SOURCE 1: https://example.org\nCONTENT: Bitcoin is a digital asset."
        result = ExecutiveEvaluator().evaluate(
            state=state,
            answer="Bitcoin es un activo digital. [S2]",
            evidence=evidence,
            selected_tools=["search"],
        )
        self.assertFalse(result.passed)
        self.assertTrue(any(reason.startswith("invalid_source_reference:") for reason in result.reasons))


    def test_research_answer_without_source_reference_is_rejected(self):
        state = decision("¿Qué es Bitcoin?")
        evidence = "SOURCE 1: https://example.org\nCONTENT: Bitcoin is a digital asset."
        result = ExecutiveEvaluator().evaluate(
            state=state,
            answer="Bitcoin es un activo digital.",
            evidence=evidence,
            selected_tools=["search"],
        )
        self.assertFalse(result.passed)
        self.assertIn("research_claim_source_reference_missing", result.reasons)

    def test_unsupported_numeric_claim_is_rejected(self):
        state = decision("¿Qué es Bitcoin?")
        evidence = "SOURCE 1: https://example.org\nCONTENT: Bitcoin is a digital asset."
        result = ExecutiveEvaluator().evaluate(
            state=state,
            answer="Bitcoin tiene un valor de 100000 dólares. [S1]",
            evidence=evidence,
            selected_tools=["search"],
        )
        self.assertFalse(result.passed)
        self.assertTrue(any(reason.startswith("unsupported_numeric_claim:") for reason in result.reasons))

if __name__ == "__main__":
    unittest.main()
