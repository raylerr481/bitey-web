import os
import unittest

from app.core.deep_research import DeepResearchEngine


@unittest.skipUnless(os.getenv("BITEY_LIVE_RESEARCH") == "1", "live web research disabled")
class LiveResearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_search_chain_uses_bounded_multistep_runtime(self):
        engine = DeepResearchEngine()
        query = "latest Python release official Python documentation"
        plan = engine.plan(query, {})
        self.assertEqual(plan.mode, "multistep")
        self.assertIn("freshness", plan.reasons)

        result = await engine.fetch(plan)

        usable = [e for e in result.evidence if e.ok and e.content]
        self.assertGreaterEqual(len(usable), 1)
        self.assertLessEqual(len(result.evidence), 20)
        self.assertTrue(any("python" in (e.title + e.url).lower() for e in usable))

    async def test_real_direct_url_evidence_path(self):
        engine = DeepResearchEngine()
        query = "https://www.python.org/"
        plan = engine.plan(query, {})
        self.assertIn("explicit_url", plan.reasons)

        result = await engine.fetch(plan)

        usable = [e for e in result.evidence if e.ok and e.content]
        self.assertGreaterEqual(len(usable), 1)
        self.assertTrue(any("python.org" in e.url for e in usable))


if __name__ == "__main__":
    unittest.main()
