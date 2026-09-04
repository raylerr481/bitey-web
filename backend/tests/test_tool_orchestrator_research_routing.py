import unittest

from app.core.tool_orchestrator import ToolOrchestrator, ToolSpec


class ResearchRoutingTests(unittest.TestCase):
    def test_research_required_prefers_bounded_runtime_when_registered(self):
        tools = ToolOrchestrator()
        async def handler(**kwargs):
            return {"ok": True}
        tools.register(ToolSpec("web_research", "bounded research", ("research",), handler))

        selected = tools.select("Investiga la última versión de Python y cita fuentes")

        self.assertIn("web_research", selected)
        self.assertNotIn("search", selected)

    def test_without_runtime_registration_search_remains_fallback(self):
        tools = ToolOrchestrator()

        selected = tools.select("Investiga la última versión de Python")

        self.assertIn("search", selected)
        self.assertNotIn("web_research", selected)

    def test_non_research_request_does_not_select_web(self):
        tools = ToolOrchestrator()

        selected = tools.select("Explícame qué es una variable en Python")

        self.assertNotIn("search", selected)
        self.assertNotIn("web_research", selected)


if __name__ == "__main__":
    unittest.main()
