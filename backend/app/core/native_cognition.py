"""Bitey native cognitive substrate.

A small, dependency-free neural-inspired model owned by Bitey. It is not a
language model: it converts perception into cognitive signals that the Brain
can use for routing, planning and verification. External models remain
optional inference tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
import re
from typing import Any


@dataclass
class CognitiveNeuron:
    name: str
    threshold: float = 0.5
    bias: float = 0.0
    activation: float = 0.0
    weights: dict[str, float] = field(default_factory=dict)

    def fire(self, inputs: dict[str, float]) -> float:
        total = self.bias + sum(inputs.get(key, 0.0) * weight for key, weight in self.weights.items())
        self.activation = 1.0 / (1.0 + exp(-total))
        return self.activation


@dataclass
class NativeCognitiveResult:
    signals: dict[str, float]
    dominant_domain: str
    research_required: bool
    reasoning_depth: str
    confidence: float
    capabilities: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "signals": {k: round(v, 4) for k, v in self.signals.items()},
            "dominant_domain": self.dominant_domain,
            "research_required": self.research_required,
            "reasoning_depth": self.reasoning_depth,
            "confidence": round(self.confidence, 4),
            "capabilities": self.capabilities,
        }


class BiteyNativeCognitiveModel:
    """Lightweight neural-inspired cognition owned by Bitey."""

    FEATURE_WORDS = {
        "research": ("investiga", "investigar", "research", "evidencia", "fuentes", "verifica", "actual", "latest"),
        "complexity": ("arquitectura", "diseña", "diseñar", "estrategia", "plan", "integra", "analiza", "debug"),
        "code": ("código", "codigo", "python", "javascript", "api", "bug", "github"),
        "trading": ("trading", "forex", "stock", "mt5", "tradingview", "bolsa"),
        "support": ("soporte", "ticket", "error", "cliente", "reparación", "repair", "cctv"),
        "marketing": ("marketing", "ventas", "campaña", "publicidad", "seo"),
        "risk": ("password", "contraseña", "secret", "api key", "token", "dinero real", "real money", "comprar", "vender", "ejecuta"),
    }

    def __init__(self) -> None:
        self.neurons = {
            "research_gate": CognitiveNeuron("research_gate", bias=-1.4, weights={"research": 2.6, "complexity": 0.7, "risk": 0.3}),
            "deep_reasoning": CognitiveNeuron("deep_reasoning", bias=-1.2, weights={"complexity": 2.8, "research": 1.0, "risk": 0.5}),
            "risk_gate": CognitiveNeuron("risk_gate", bias=-1.5, weights={"risk": 3.2, "trading": 0.4}),
        }
        self.learning_rate = 0.03

    def analyze(self, message: str, context: dict[str, Any] | None = None) -> NativeCognitiveResult:
        text = f" {message.lower().strip()} "
        features = {name: self._feature_score(text, words) for name, words in self.FEATURE_WORDS.items()}
        signals = {name: neuron.fire(features) for name, neuron in self.neurons.items()}
        domains = {name: features[name] for name in ("trading", "support", "code", "marketing")}
        dominant = max(domains, key=domains.get) if max(domains.values(), default=0.0) > 0 else "general"
        research = signals["research_gate"] >= 0.62
        deep = signals["deep_reasoning"] >= 0.62
        depth = "deep" if deep else "structured" if signals["deep_reasoning"] >= 0.42 else "direct"
        confidence = min(0.98, 0.45 + max(signals.values()) * 0.45)
        capabilities = ["native_perception", "native_intent_signal", "native_reasoning_routing", "native_risk_signal"]
        if research:
            capabilities.append("bounded_research")
        if context and context.get("evidence_available"):
            capabilities.append("evidence_aware")
        return NativeCognitiveResult(signals, dominant, research, depth, confidence, capabilities)

    def learn(self, features: dict[str, float], outcome: float) -> None:
        """Small bounded Hebbian-style update from evaluator feedback."""
        target = max(0.0, min(1.0, outcome))
        for neuron in self.neurons.values():
            error = target - neuron.activation
            for key in list(neuron.weights):
                neuron.weights[key] += self.learning_rate * error * features.get(key, 0.0)
                neuron.weights[key] = max(-4.0, min(4.0, neuron.weights[key]))

    @staticmethod
    def _feature_score(text: str, words: tuple[str, ...]) -> float:
        hits = sum(1 for word in words if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text))
        return min(1.0, hits / 3.0)

    def status(self) -> dict[str, Any]:
        return {
            "name": "Bitey Native Cognitive Model",
            "version": "0.1.0",
            "type": "neural_inspired_symbolic_substrate",
            "provider_independent": True,
            "generates_language": False,
            "external_models_optional": True,
            "learning": "bounded_hebbian_feedback",
            "neurons": list(self.neurons),
        }
