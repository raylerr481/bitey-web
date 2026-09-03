import unittest

from app.core.context_engine import ContextEngine
from app.core.research_engine import ResearchEngine
from app.core.ollama_provider import OllamaProvider


class CognitiveCoreTests(unittest.TestCase):
    def test_context_is_dynamic_and_enterprise_optional(self):
        envelope = ContextEngine().assemble(
            message="Explain quantum computing",
            metadata={"user": {"id": "u1"}, "channel": {"type": "web"}},
        )
        self.assertIsNone(envelope.enterprise)
        self.assertEqual(envelope.task["message"], "Explain quantum computing")

    def test_research_is_triggered_for_freshness(self):
        plan = ResearchEngine().plan("What is the latest AI model?", {})
        self.assertTrue(plan.required)
        self.assertIn("freshness_sensitive", plan.reasons)

    def test_ollama_defaults_to_local_endpoint(self):
        provider = OllamaProvider()
        self.assertEqual(provider.base_url, "http://127.0.0.1:11434")
        self.assertTrue(provider.free_only)


if __name__ == "__main__":
    unittest.main()
