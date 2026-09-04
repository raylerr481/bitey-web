import unittest

from app.core.evidence_engine import EvidenceEngine


class EvidenceEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = EvidenceEngine()

    def test_trusted_fresh_direct_evidence_passes(self):
        decision = self.engine.assess(
            "What is the latest Python release?",
            [{
                "url": "https://docs.python.org/3/",
                "ok": True,
                "title": "Python Documentation",
                "content": "Python documentation for the current 2026 release and the latest Python language reference."
            }],
        )
        self.assertTrue(decision.sufficient)
        self.assertGreaterEqual(decision.confidence, 0.70)
        self.assertEqual(decision.assessments[0].source_reliability, 0.99)

    def test_no_evidence_fails_closed(self):
        decision = self.engine.assess("research something", [])
        self.assertFalse(decision.sufficient)
        self.assertEqual(decision.confidence, 0.0)
        self.assertIn("no_usable_evidence", decision.reasons)

    def test_contradiction_blocks_decision(self):
        decision = self.engine.assess(
            "Compare current Python release information",
            [
                {"url": "https://python.org", "ok": True, "content": "Python 2026 is the current release and is supported."},
                {"url": "https://example.com", "ok": True, "content": "However, Python 2026 is not the current release; another version is current instead."},
            ],
        )
        self.assertTrue(decision.contradiction_detected)
        self.assertFalse(decision.sufficient)
        self.assertIn("contradiction_detected", decision.reasons)

    def test_unusable_entries_are_ignored(self):
        decision = self.engine.assess(
            "Explain Python",
            [{"url": "https://python.org", "ok": False, "content": ""}],
        )
        self.assertFalse(decision.sufficient)
        self.assertEqual(decision.assessments, [])


if __name__ == "__main__":
    unittest.main()
