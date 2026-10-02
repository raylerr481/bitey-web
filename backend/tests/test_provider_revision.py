import unittest

from app.core.provider_gateway import ProviderGateway


class FakeProvider:
    name = "fake-free"
    priority = 1
    free_only = True

    def __init__(self):
        self.calls = 0

    async def health(self):
        return True

    async def generate(self, *, messages, context):
        self.calls += 1
        return f"Respuesta de prueba {self.calls} sin evidencia verificable suficiente."


class BoundedProviderRevisionTests(unittest.IsolatedAsyncioTestCase):

    def test_free_provider_cascade_is_groq_openrouter_local_native(self):
        gateway = ProviderGateway.__new__(ProviderGateway)
        gateway.ROLE_PREFERENCES = ProviderGateway.ROLE_PREFERENCES
        providers = []
        for name, priority in (
            ("bitey-native-cognitive-v1", 2),
            ("ollama-local", 1),
            ("openrouter-free-test", 90),
            ("groq-free", 50),
            ("deepseek-free", 70),
        ):
            p = FakeProvider()
            p.name = name
            p.priority = priority
            providers.append(p)

        ordered = gateway._order_for_role(providers, "synthesis")
        self.assertEqual(
            [p.name for p in ordered],
            ["ollama-local", "groq-free", "deepseek-free", "openrouter-free-test", "bitey-native-cognitive-v1"],
        )

    async def test_revision_is_bounded_to_one_attempt(self):
        gateway = ProviderGateway.__new__(ProviderGateway)
        provider = FakeProvider()
        gateway._providers = {provider.name: provider}
        gateway._conversation_provider = {}
        gateway._openrouter_catalog_loaded = True
        gateway._openrouter_catalog_loaded_at = 0.0
        gateway._prepare_external_free_providers = lambda: None

        # Avoid the async preparation path entirely while preserving the real gateway loop.
        async def prepare():
            return None

        gateway._prepare_external_free_providers = prepare

        context = {
            "bitey_brain": {
                "model_role": "evidence_grounded_synthesis",
                "evidence_required": True,
                "tool_priority": [],
                "risk_level": "low",
                "execution_allowed": False,
                "verification_required": False,
            },
            "selected_tools": [],
            "evidence_available": False,
        }

        answer = await gateway.generate(
            messages=[{"role": "user", "content": "Investiga una opción actual."}],
            context=context,
        )

        self.assertTrue(answer)
        self.assertEqual(provider.calls, 2, "Bitey debe permitir como máximo una revisión")
        self.assertTrue(context.get("executive_revision_attempted"))
        self.assertEqual(context["executive_evaluation"]["decision"], "revise")

    async def test_compliant_generation_does_not_trigger_revision(self):
        gateway = ProviderGateway.__new__(ProviderGateway)
        provider = FakeProvider()
        gateway._providers = {provider.name: provider}
        gateway._conversation_provider = {}
        gateway._openrouter_catalog_loaded = True
        gateway._openrouter_catalog_loaded_at = 0.0

        async def prepare():
            return None

        gateway._prepare_external_free_providers = prepare

        context = {
            "bitey_brain": {
                "model_role": "synthesis",
                "evidence_required": False,
                "tool_priority": [],
                "risk_level": "low",
                "execution_allowed": False,
                "verification_required": False,
            },
            "selected_tools": [],
            "evidence_available": False,
        }

        answer = await gateway.generate(
            messages=[{"role": "user", "content": "Explica qué es una API."}],
            context=context,
        )

        self.assertTrue(answer)
        self.assertEqual(provider.calls, 1)
        self.assertFalse(context.get("executive_revision_attempted", False))
        self.assertEqual(context["executive_evaluation"]["decision"], "accept")


if __name__ == "__main__":
    unittest.main()
