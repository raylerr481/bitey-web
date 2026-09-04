import unittest

from app.core.bitey_brain import BiteyBrain
from app.core.research_engine import ResearchEngine
from app.core.tool_orchestrator import ToolOrchestrator, ToolSpec


class ResearchExecutionRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_research_request_selects_web_research_once(self):
        orchestrator = ToolOrchestrator()
        calls = []

        async def fake_web_research(message: str, context=None):
            calls.append(message)
            return {"ok": True, "evidence": "SOURCE: official evidence"}

        orchestrator.register(
            ToolSpec(
                "web_research",
                "test bounded research runtime",
                ("web", "research", "evidence"),
                fake_web_research,
            )
        )

        context = {}
        plan = ResearchEngine().plan("Investiga la última versión de Python y cita fuentes", context)
        selected = orchestrator.select("Investiga la última versión de Python y cita fuentes", context)
        self.assertTrue(plan.required)
        self.assertEqual(selected.count("web_research"), 1)
        self.assertNotIn("search", selected)

        results = await orchestrator.execute(selected, message="Investiga la última versión de Python y cita fuentes", context=context)
        self.assertEqual(len(calls), 1)
        self.assertIn("evidence", results["web_research"])

        context["evidence_available"] = bool(results["web_research"].get("evidence"))
        state = BiteyBrain().think("Investiga la última versión de Python y cita fuentes", context)
        self.assertTrue(state.evidence_required)
        self.assertEqual(state.reasoning_mode, "evidence_first")

        # Once evidence exists, the main execution path must not trigger the
        # fallback deep-research branch a second time.
        fallback_needed = not results["web_research"].get("evidence") and plan.required
        self.assertFalse(fallback_needed)
        self.assertEqual(len(calls), 1)

    async def test_ordinary_request_does_not_select_web_research(self):
        orchestrator = ToolOrchestrator()
        context = {}
        ResearchEngine().plan("Explícame qué es una variable en Python", context)
        selected = orchestrator.select("Explícame qué es una variable en Python", context)
        self.assertNotIn("web_research", selected)
        self.assertNotIn("search", selected)


if __name__ == "__main__":
    unittest.main()
