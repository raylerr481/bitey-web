import unittest

from app.core.bitey_brain import BiteyBrain
from app.core.cognitive_model import CognitiveModel


class GeneralSpecializedBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.cognition = CognitiveModel()
        self.brain = BiteyBrain()

    def assert_general(self, message):
        state = self.cognition.process(message, {})
        self.assertEqual(state.intention["domain"], "general", message)
        brain = self.brain.think(message, {"cognition": state.as_dict()})
        self.assertEqual(brain.task_class, "general", message)
        self.assertNotIn("risk_guard", brain.required_capabilities)
        self.assertIn("GENERAL-DOMAIN BOUNDARY", self.brain.system_directive(brain))

    def assert_trading(self, message):
        state = self.cognition.process(message, {})
        self.assertEqual(state.intention["domain"], "trading", message)
        brain = self.brain.think(message, {"cognition": state.as_dict()})
        self.assertEqual(brain.task_class, "trading", message)
        self.assertIn("risk_guard", brain.required_capabilities)
        self.assertIn("TRADING-DOMAIN BOUNDARY", self.brain.system_directive(brain))

    def test_bitcoin_concept_is_general(self):
        self.assert_general("¿Qué es Bitcoin?")

    def test_blockchain_concept_is_general(self):
        self.assert_general("¿Qué es blockchain?")

    def test_trading_concept_is_general(self):
        self.assert_general("¿Qué es trading?")

    def test_btc_m1_analysis_is_trading(self):
        self.assert_trading("Analiza BTCUSDT en M1")

    def test_trading_signal_is_trading(self):
        self.assert_trading("Dame una señal de trading para BTCUSD")

    def test_backtest_is_trading(self):
        self.assert_trading("Haz un backtest de BTCUSD")

    def test_previous_trading_context_cannot_hijack_bitcoin_question(self):
        previous = self.cognition.process("Analiza BTCUSDT en M1", {})
        current = self.cognition.process(
            "¿Qué es Bitcoin?",
            {"domain": previous.intention["domain"], "_cognitive_state": previous},
        )
        self.assertEqual(current.intention["domain"], "general")


if __name__ == "__main__":
    unittest.main()
