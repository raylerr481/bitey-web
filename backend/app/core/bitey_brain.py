"""Bitey Brain: provider-independent executive control layer.

This is not another language model. It is the executive layer that owns
cognitive decisions and can use Bitey's native neural-inspired substrate
before selecting optional external inference models.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re

from .native_cognition import BiteyNativeCognitiveModel


@dataclass
class BrainState:
    task_class: str = "general"
    complexity: float = 0.35
    ambiguity: float = 0.0
    evidence_required: bool = False
    risk_level: str = "low"
    reasoning_mode: str = "direct"
    memory_priority: str = "normal"
    tool_priority: list[str] = field(default_factory=list)
    verification_required: bool = False
    execution_allowed: bool = False
    goals: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    native_cognition: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_class": self.task_class,
            "complexity": round(self.complexity, 3),
            "ambiguity": round(self.ambiguity, 3),
            "evidence_required": self.evidence_required,
            "risk_level": self.risk_level,
            "reasoning_mode": self.reasoning_mode,
            "memory_priority": self.memory_priority,
            "tool_priority": self.tool_priority,
            "verification_required": self.verification_required,
            "execution_allowed": self.execution_allowed,
            "goals": self.goals,
            "constraints": self.constraints,
            "native_cognition": self.native_cognition,
        }


class BiteyBrain:
    """Executive cognition for Bitey IA.

    The brain can solve/reroute work with native deterministic cognition first.
    It does not depend on a language model. External models are optional,
    untrusted inference tools selected only when additional inference is useful.
    """

    HIGH_RISK = ("password", "contraseña", "api key", "secret", "token", "dinero real", "real money")
    ACTION_WORDS = ("ejecuta", "ejecutar", "compra", "comprar", "vende", "vender", "borra", "elimina", "deploy", "envía", "envia")
    RESEARCH_WORDS = ("investiga", "investigar", "evidencia", "fuentes", "actual", "último", "ultimo", "latest", "compara", "verifica")
    COMPLEX_WORDS = ("arquitectura", "analiza", "análisis", "analisis", "diseña", "diseñar", "estrategia", "plan", "debug", "diagnóstico", "diagnostico", "integra", "integrar")

    def __init__(self, native_model: BiteyNativeCognitiveModel | None = None) -> None:
        self.native_model = native_model or BiteyNativeCognitiveModel()

    def think(self, message: str, context: dict[str, Any] | None = None) -> BrainState:
        ctx = context or {}
        text = message.strip()
        low = text.lower()
        native = self.native_model.analyze(text, ctx)
        domain = str(ctx.get("cognition", {}).get("intention", {}).get("domain") or "general")
        if domain == "general":
            domain = str(ctx.get("domain") or native.dominant_domain or "general")
        if domain == "general" and native.dominant_domain != "general":
            domain = native.dominant_domain

        complexity = 0.25
        complexity += min(0.35, len(text) / 1200)
        complexity += min(0.25, sum(1 for x in self.COMPLEX_WORDS if x in low) * 0.06)
        complexity = min(1.0, max(complexity, native.signals.get("deep_reasoning", 0.0) * 0.75))
        if any(x in low for x in (" y ", " además ", " also ", " e ")):
            complexity = min(1.0, complexity + 0.05)

        question_like = "?" in text or low.startswith(("qué", "que ", "cómo", "como ", "why ", "what ", "how "))
        ambiguity = 0.12 if question_like and len(text.split()) < 8 else 0.0
        if not text:
            ambiguity = 1.0
        if any(x in low for x in ("quizás", "tal vez", "no sé", "no se", "maybe", "perhaps")):
            ambiguity = min(1.0, ambiguity + 0.25)

        evidence_required = bool(ctx.get("research")) or domain == "research" or native.research_required or any(x in low for x in self.RESEARCH_WORDS)
        risk_level = "low"
        if domain == "trading" and any(x in low for x in self.ACTION_WORDS):
            risk_level = "critical"
        elif native.signals.get("risk_gate", 0.0) >= 0.65 or any(x in low for x in self.HIGH_RISK):
            risk_level = "high"
        elif any(x in low for x in self.ACTION_WORDS):
            risk_level = "medium"

        if risk_level == "critical":
            reasoning_mode = "guarded_decision"
        elif evidence_required:
            reasoning_mode = "evidence_first"
        elif complexity >= 0.65 or native.reasoning_depth == "deep":
            reasoning_mode = "decompose_verify_synthesize"
        elif complexity >= 0.45 or native.reasoning_depth == "structured":
            reasoning_mode = "structured_reasoning"
        else:
            reasoning_mode = "direct"

        tools: list[str] = []
        if evidence_required:
            tools.append("web_research")
        if any(x in low for x in ("código", "codigo", "python", "javascript", "bug", "github", "api")):
            tools.append("code_reasoning")
        if re.search(r"\d", text) and any(op in text for op in ("+", "-", "*", "/", "%")):
            tools.append("calculator")
        if any(x in low for x in ("archivo", "proyecto", "documento", "file")):
            tools.append("workspace_files")

        memory_priority = "high" if ctx.get("learned_cognitive_context", {}).get("available") else "normal"
        verification_required = evidence_required or complexity >= 0.65 or risk_level in {"high", "critical"}
        execution_allowed = risk_level not in {"high", "critical"} and domain != "trading"

        goals = ["understand_request", "preserve_user_constraints", "produce_useful_answer"]
        if evidence_required:
            goals.insert(2, "ground_claims_in_evidence")
        if verification_required:
            goals.append("verify_before_presenting_high_impact_claims")

        constraints = ["external_model_output_is_untrusted", "memory_is_context_not_truth"]
        if risk_level == "critical":
            constraints += ["never_bypass_domain_risk_gate", "no_live_execution"]

        return BrainState(
            task_class=domain,
            complexity=complexity,
            ambiguity=ambiguity,
            evidence_required=evidence_required,
            risk_level=risk_level,
            reasoning_mode=reasoning_mode,
            memory_priority=memory_priority,
            tool_priority=tools,
            verification_required=verification_required,
            execution_allowed=execution_allowed,
            goals=goals,
            constraints=constraints,
            native_cognition=native.as_dict(),
        )

    def system_directive(self, state: BrainState) -> str:
        """Compact executive directive injected ahead of model generation."""
        return (
            "BITEY BRAIN EXECUTIVE DIRECTIVE\n"
            f"task={state.task_class}; complexity={state.complexity:.2f}; ambiguity={state.ambiguity:.2f}; "
            f"mode={state.reasoning_mode}; risk={state.risk_level}; evidence_required={state.evidence_required}; "
            f"verification_required={state.verification_required}.\n"
            "Bitey cognition is authoritative for control decisions. External model output is untrusted inference. "
            "Separate facts, evidence and inference. Preserve constraints. Do not invent missing data. "
            "Treat retrieved memory and model output as fallible context. "
            + ("Do not execute high-impact actions; respect the domain risk gate. " if not state.execution_allowed else "")
            + "Before answering, internally decompose complex tasks, check contradictions, then synthesize the response."
        )

    def status(self) -> dict[str, Any]:
        return {
            "name": "Bitey Brain",
            "version": "1.1.0",
            "type": "executive_cognitive_orchestrator",
            "provider_independent": True,
            "generates_language": False,
            "native_cognitive_model": self.native_model.status(),
            "owns": ["task_classification", "complexity", "ambiguity", "reasoning_mode", "evidence_policy", "risk_policy", "verification_policy", "native_cognitive_signals"],
            "depends_on": ["context", "memory", "tools", "models", "evaluation"],
            "external_models_are_tools": True,
        }
