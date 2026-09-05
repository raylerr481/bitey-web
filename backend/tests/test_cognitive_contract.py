import unittest

from app.core.bitey_brain import BiteyBrain
from app.core.cognitive_model import CognitiveModel
from app.core.tool_orchestrator import ToolOrchestrator
from app.core.executive_evaluator import ExecutiveEvaluator


def decision(message: str, context: dict | None = None):
    ctx = dict(context or {})
    cognition = CognitiveModel().process(message, ctx, evidence_available=bool(ctx.get("evidence_available")))
    ctx["cognition"] = cognition.as_dict()
    return BiteyBrain().think(message, ctx)


class CognitiveContractTests(unittest.TestCase):
    def test_brain_decides_before_provider_role(self):
        state = decision("Explícame cómo funciona una API REST")
        self.assertTrue(state.model_role)
        self.assertIn("model_selection_follows_cognitive_plan", state.constraints)

    def test_brain_does_not_reuse_different_request(self):
        brain = BiteyBrain()
        ctx = {"cognition": CognitiveModel().process("¿Qué clima hace ahora en Esteio?", {}, evidence_available=False).as_dict()}
        first = brain.think("¿Qué clima hace ahora en Esteio?", ctx)
        ctx["cognition"] = CognitiveModel().process("Explica Python", {}, evidence_available=False).as_dict()
        second = brain.think("Explica Python", ctx)
        self.assertNotEqual(first.decision_fingerprint, second.decision_fingerprint)
        self.assertNotEqual(first.task_class, second.task_class)

    def test_weather_requires_specialized_tool_and_freshness(self):
        state = decision("¿Qué temperatura hace ahora en Esteio?")
        self.assertEqual(state.task_class, "weather")
        self.assertTrue(state.freshness_required)
        self.assertTrue(state.evidence_required)
        self.assertEqual(state.tool_priority, ["weather"])

    def test_research_requires_search_evidence(self):
        state = decision("Investiga y compara las opciones actuales para una API gratuita")
        self.assertTrue(state.evidence_required)
        self.assertIn("web_research", state.tool_priority)
        self.assertIn("external_evidence", state.required_capabilities)

    def test_trading_action_is_blocked(self):
        state = decision("Compra EURUSD con dinero real")
        self.assertEqual(state.task_class, "trading")
        self.assertEqual(state.risk_level, "critical")
        self.assertFalse(state.execution_allowed)
        self.assertIn("risk_guard", state.required_capabilities)

    def test_tool_orchestrator_selection_uses_brain_policy(self):
        orchestrator = ToolOrchestrator()
        ctx = {}
        selected = orchestrator.select("¿Cuál es el clima actual en Esteio?", ctx)
        self.assertEqual(selected, ["weather"])
        self.assertTrue(ctx["bitey_brain"]["freshness_required"])
        self.assertEqual(ctx["selected_tools"], ["weather"])

    def test_executive_evaluator_accepts_compliant_output(self):
        state = decision("Investiga las opciones actuales de APIs gratuitas")
        result = ExecutiveEvaluator().evaluate(state=state, answer="La investigación compara varias opciones y sus límites.", evidence="source A; source B", selected_tools=["web_research"])
        self.assertTrue(result.passed)
        self.assertEqual(result.decision, "accept")
        self.assertTrue(result.provider_independent)

    def test_executive_evaluator_rejects_missing_required_evidence(self):
        state = decision("Investiga las opciones actuales de APIs gratuitas")
        result = ExecutiveEvaluator().evaluate(state=state, answer="Estas son las mejores opciones actuales.", evidence="", selected_tools=[])
        self.assertFalse(result.passed)
        self.assertEqual(result.decision, "revise")
        self.assertIn("required_evidence_missing", result.reasons)


if __name__ == "__main__":
    unittest.main()
