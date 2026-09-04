"""Bitey Brain: provider-independent executive decision layer.

The Brain decides WHAT must happen before any provider/model is selected.
Models are inference workers and never become the executive controller.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re


@dataclass
class BrainState:
    task_class: str = "general"
    objective: str = "answer_or_assist"
    complexity: float = 0.35
    ambiguity: float = 0.0
    evidence_required: bool = False
    freshness_required: bool = False
    risk_level: str = "low"
    reasoning_mode: str = "direct"
    memory_priority: str = "normal"
    required_capabilities: list[str] = field(default_factory=list)
    tool_priority: list[str] = field(default_factory=list)
    verification_required: bool = False
    execution_allowed: bool = False
    model_role: str = "synthesis"
    model_selection_reason: str = "default_synthesis"
    stop_condition: str = "sufficient_confidence"
    goals: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_class": self.task_class,
            "objective": self.objective,
            "complexity": round(self.complexity, 3),
            "ambiguity": round(self.ambiguity, 3),
            "evidence_required": self.evidence_required,
            "freshness_required": self.freshness_required,
            "risk_level": self.risk_level,
            "reasoning_mode": self.reasoning_mode,
            "memory_priority": self.memory_priority,
            "required_capabilities": self.required_capabilities,
            "tool_priority": self.tool_priority,
            "verification_required": self.verification_required,
            "execution_allowed": self.execution_allowed,
            "model_role": self.model_role,
            "model_selection_reason": self.model_selection_reason,
            "stop_condition": self.stop_condition,
            "goals": self.goals,
            "constraints": self.constraints,
        }


class BiteyBrain:
    """Executive cognition.

    Decision order is explicit:
      1. understand the task state;
      2. determine capabilities/evidence/actions required;
      3. choose reasoning and verification policy;
      4. only then describe the model role required for inference.

    This keeps model selection downstream of cognition and prevents a provider
    from deciding which tools, evidence or actions Bitey should use.
    """

    HIGH_RISK = ("password", "contraseña", "api key", "secret", "token", "dinero real", "real money")
    ACTION_WORDS = ("ejecuta", "ejecutar", "compra", "comprar", "vende", "vender", "borra", "elimina", "deploy", "envía", "envia")
    FRESHNESS_WORDS = ("ahora", "actualmente", "hoy", "último", "ultimo", "reciente", "latest", "current", "recent", "en vivo", "tiempo real")

    def think(self, message: str, context: dict[str, Any] | None = None) -> BrainState:
        ctx = context or {}
        text = message.strip()
        low = text.lower()
        cognition = ctx.get("cognition") or {}
        intention = cognition.get("intention") or {}
        perception = cognition.get("perception") or {}
        domain = str(intention.get("domain") or ctx.get("domain") or "general")

        complexity = self._complexity(text, cognition)
        question_like = bool(perception.get("question")) or "?" in text
        ambiguity = float(cognition.get("ambiguity", 0.0) or 0.0)
        if question_like and len(text.split()) < 8:
            ambiguity = max(ambiguity, 0.12)
        if not text:
            ambiguity = 1.0

        freshness_required = bool(ctx.get("freshness_required") or cognition.get("plan", {}).get("freshness_required")) or any(x in low for x in self.FRESHNESS_WORDS)
        evidence_required = bool(ctx.get("requires_web_research") or ctx.get("needs_web") or ctx.get("research") or ctx.get("evidence_available") or cognition.get("plan", {}).get("needs_evidence")) or freshness_required

        risk_level = "low"
        if domain == "trading" and any(x in low for x in self.ACTION_WORDS):
            risk_level = "critical"
        elif any(x in low for x in self.HIGH_RISK):
            risk_level = "high"
        elif any(x in low for x in self.ACTION_WORDS):
            risk_level = "medium"

        capabilities = self._capabilities(domain, evidence_required, freshness_required, complexity, ctx)
        tools = self._tool_policy(capabilities, domain, ctx)
        verification_required = evidence_required or complexity >= 0.60 or risk_level in {"high", "critical"}

        if risk_level == "critical":
            reasoning_mode = "guarded_decision"
        elif evidence_required and complexity >= 0.60:
            reasoning_mode = "research_decompose_verify_synthesize"
        elif evidence_required:
            reasoning_mode = "evidence_first"
        elif complexity >= 0.60:
            reasoning_mode = "decompose_verify_synthesize"
        elif complexity >= 0.42:
            reasoning_mode = "structured_reasoning"
        else:
            reasoning_mode = "direct"

        model_role, model_reason = self._model_policy(
            domain=domain,
            complexity=complexity,
            evidence_required=evidence_required,
            required_capabilities=capabilities,
            verification_required=verification_required,
        )

        memory_priority = "high" if ctx.get("learned_cognitive_context", {}).get("available") else "normal"
        execution_allowed = risk_level not in {"high", "critical"} and domain != "trading"
        stop_condition = "verified_evidence_and_sufficient_confidence" if verification_required else "sufficient_confidence"

        goals = ["understand_request", "preserve_user_constraints", "select_required_capabilities", "produce_useful_answer"]
        if evidence_required:
            goals.insert(3, "ground_claims_in_evidence")
        if verification_required:
            goals.append("verify_before_presenting_high_impact_claims")

        constraints = ["external_model_output_is_untrusted", "memory_is_context_not_truth", "model_selection_follows_cognitive_plan"]
        if risk_level == "critical":
            constraints += ["never_bypass_domain_risk_gate", "no_live_execution"]

        return BrainState(
            task_class=domain,
            objective=self._objective(capabilities, domain),
            complexity=complexity,
            ambiguity=max(0.0, min(1.0, ambiguity)),
            evidence_required=evidence_required,
            freshness_required=freshness_required,
            risk_level=risk_level,
            reasoning_mode=reasoning_mode,
            memory_priority=memory_priority,
            required_capabilities=capabilities,
            tool_priority=tools,
            verification_required=verification_required,
            execution_allowed=execution_allowed,
            model_role=model_role,
            model_selection_reason=model_reason,
            stop_condition=stop_condition,
            goals=goals,
            constraints=constraints,
        )

    @staticmethod
    def _complexity(text: str, cognition: dict[str, Any]) -> float:
        perception = cognition.get("perception") or {}
        explicit = perception.get("complexity")
        if isinstance(explicit, (int, float)):
            return max(0.0, min(1.0, float(explicit)))
        tokens = len(text.split())
        base = 0.22 + min(0.30, tokens / 180)
        plan = cognition.get("plan") or {}
        if plan.get("needs_evidence"):
            base += 0.12
        if plan.get("requires_specialized_module"):
            base += 0.08
        if any(x in text.lower() for x in (" y ", " además ", " also ", " e ", ";")):
            base += 0.05
        return min(1.0, base)

    @staticmethod
    def _capabilities(domain: str, evidence: bool, freshness: bool, complexity: float, context: dict[str, Any]) -> list[str]:
        capabilities: list[str] = ["conversation"]
        if evidence:
            capabilities.append("external_evidence")
        if freshness:
            capabilities.append("fresh_data")
        if complexity >= 0.60:
            capabilities.append("multi_step_reasoning")
        if domain == "research":
            capabilities += ["source_comparison", "research_synthesis"]
        if domain == "programming":
            capabilities.append("code_reasoning")
        if domain == "trading":
            capabilities.append("risk_guard")
        requested = context.get("required_capabilities") or []
        for item in requested:
            if item not in capabilities:
                capabilities.append(str(item))
        return capabilities

    @staticmethod
    def _tool_policy(capabilities: list[str], domain: str, context: dict[str, Any]) -> list[str]:
        tools: list[str] = []
        if "fresh_data" in capabilities and domain == "weather":
            tools.append("weather")
        if "external_evidence" in capabilities and "weather" not in tools:
            tools.append("search")
        if "code_reasoning" in capabilities:
            tools.append("code_reasoning")
        if context.get("workspace_files_required"):
            tools.append("workspace_files")
        return tools

    @staticmethod
    def _objective(capabilities: list[str], domain: str) -> str:
        if "research_synthesis" in capabilities:
            return "research_and_synthesize"
        if "fresh_data" in capabilities:
            return "retrieve_current_data_and_answer"
        if "code_reasoning" in capabilities:
            return "reason_about_or_create_code"
        if domain == "trading":
            return "analyze_under_risk_policy"
        return "answer_or_assist"

    @staticmethod
    def _model_policy(*, domain: str, complexity: float, evidence_required: bool, required_capabilities: list[str], verification_required: bool) -> tuple[str, str]:
        # This is a role decision, not a provider-name decision. ProviderGateway
        # resolves the concrete available model only after this contract exists.
        if "research_synthesis" in required_capabilities or complexity >= 0.75:
            return "strong_reasoning_synthesis", "high_complexity_or_research"
        if verification_required or evidence_required:
            return "evidence_grounded_synthesis", "evidence_or_verification_required"
        if "code_reasoning" in required_capabilities:
            return "code_reasoning", "programming_capability_required"
        if domain == "trading":
            return "guarded_analysis", "trading_risk_policy"
        return "fast_synthesis", "low_complexity_direct_response"

    def system_directive(self, state: BrainState) -> str:
        return (
            "BITEY BRAIN EXECUTIVE CONTRACT\n"
            f"objective={state.objective}; task={state.task_class}; mode={state.reasoning_mode}; "
            f"capabilities={','.join(state.required_capabilities)}; tools={','.join(state.tool_priority) or 'none'}; "
            f"model_role={state.model_role}; risk={state.risk_level}; evidence_required={state.evidence_required}; "
            f"freshness_required={state.freshness_required}; verification_required={state.verification_required}.\n"
            "Bitey has already decided what must be done. The selected model is only an inference/synthesis worker. "
            "Do not invent facts, bypass tool/evidence requirements, or override the cognitive contract."
        )

    def status(self) -> dict[str, Any]:
        return {
            "name": "Bitey Brain",
            "version": "2.0.0",
            "type": "executive_cognitive_decision_layer",
            "provider_independent": True,
            "generates_language": False,
            "decides_before_model_selection": True,
            "owns": ["objective", "capabilities", "tool_policy", "evidence_policy", "reasoning_policy", "verification_policy", "model_role_policy", "risk_policy"],
            "depends_on": ["perception", "intention", "context", "memory", "evidence", "tools", "evaluation"],
            "external_models_are_tools": True,
        }
