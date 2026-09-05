"""Bitey Brain: provider-independent executive decision layer."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import hashlib

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
    decision_fingerprint: str = ""
    def as_dict(self) -> dict[str, Any]: return {k: getattr(self, k) for k in self.__dataclass_fields__}

class BiteyBrain:
    """Executive cognition. It decides WHAT must happen before model selection."""
    HIGH_RISK = ("password", "contraseña", "api key", "secret", "token", "dinero real", "real money")
    ACTION_WORDS = ("ejecuta", "ejecutar", "compra", "comprar", "vende", "vender", "borra", "elimina", "deploy", "envía", "envia")
    FRESHNESS_WORDS = ("ahora", "actualmente", "hoy", "último", "ultimo", "reciente", "latest", "current", "recent", "en vivo", "tiempo real")
    EVIDENCE_WORDS = ("investiga", "investigar", "investigue", "compara", "comparar", "compara la", "fuentes", "verifica las fuentes", "evidencia", "research", "compare", "sources", "verify")

    def _fingerprint(self, message: str, context: dict[str, Any], evidence_available: bool) -> str:
        cognition = context.get("cognition") or {}; intention = cognition.get("intention") or {}; plan = cognition.get("plan") or {}
        material = {"message": message.strip(), "domain": intention.get("domain") or context.get("domain") or "general", "evidence": evidence_available, "freshness": context.get("freshness_required"), "research": context.get("research"), "needs_web": context.get("needs_web"), "capabilities": sorted(map(str, context.get("required_capabilities") or [])), "plan_evidence": plan.get("needs_evidence")}
        return hashlib.sha256(repr(sorted(material.items())).encode("utf-8")).hexdigest()[:16]

    def think(self, message: str, context: dict[str, Any] | None = None) -> BrainState:
        ctx = context if context is not None else {}; text = message.strip(); low = text.lower()
        cognition = ctx.get("cognition") or {}; intention = cognition.get("intention") or {}; perception = cognition.get("perception") or {}; domain = str(intention.get("domain") or ctx.get("domain") or "general")
        evidence_available = bool(ctx.get("evidence_available")); fingerprint = self._fingerprint(message, ctx, evidence_available)
        cached = ctx.get("_bitey_brain_state")
        if isinstance(cached, BrainState) and cached.decision_fingerprint == fingerprint: return cached
        complexity = self._complexity(text, cognition); ambiguity = float(cognition.get("ambiguity", 0.0) or 0.0)
        if (bool(perception.get("question")) or "?" in text) and len(text.split()) < 8: ambiguity = max(ambiguity, 0.12)
        if not text: ambiguity = 1.0
        freshness = bool(ctx.get("freshness_required") or cognition.get("plan", {}).get("freshness_required")) or any(x in low for x in self.FRESHNESS_WORDS)
        evidence = bool(ctx.get("requires_web_research") or ctx.get("needs_web") or ctx.get("research") or evidence_available or cognition.get("plan", {}).get("needs_evidence")) or freshness or any(x in low for x in self.EVIDENCE_WORDS)
        risk = "low"
        if domain == "trading" and any(x in low for x in self.ACTION_WORDS): risk = "critical"
        elif any(x in low for x in self.HIGH_RISK): risk = "high"
        elif any(x in low for x in self.ACTION_WORDS): risk = "medium"
        capabilities = self._capabilities(domain, evidence, freshness, complexity, ctx); tools = self._tool_policy(capabilities, domain, ctx); verification = evidence or complexity >= .60 or risk in {"high", "critical"}
        mode = "guarded_decision" if risk == "critical" else "research_decompose_verify_synthesize" if evidence and complexity >= .60 else "evidence_first" if evidence else "decompose_verify_synthesize" if complexity >= .60 else "structured_reasoning" if complexity >= .42 else "direct"
        role, reason = self._model_policy(domain=domain, complexity=complexity, evidence_required=evidence, required_capabilities=capabilities, verification_required=verification)
        state = BrainState(task_class=domain, objective=self._objective(capabilities, domain), complexity=complexity, ambiguity=max(0,min(1,ambiguity)), evidence_required=evidence, freshness_required=freshness, risk_level=risk, reasoning_mode=mode, memory_priority="high" if ctx.get("learned_cognitive_context", {}).get("available") else "normal", required_capabilities=capabilities, tool_priority=tools, verification_required=verification, execution_allowed=risk not in {"high","critical"} and domain != "trading", model_role=role, model_selection_reason=reason, stop_condition="verified_evidence_and_sufficient_confidence" if verification else "sufficient_confidence", goals=["understand_request","preserve_user_constraints","select_required_capabilities","produce_useful_answer"], constraints=["external_model_output_is_untrusted","memory_is_context_not_truth","model_selection_follows_cognitive_plan"], decision_fingerprint=fingerprint)
        if evidence: state.goals.insert(3,"ground_claims_in_evidence")
        if verification: state.goals.append("verify_before_presenting_high_impact_claims")
        if risk == "critical": state.constraints += ["never_bypass_domain_risk_gate","no_live_execution"]
        ctx["_bitey_brain_state"] = state; ctx["_bitey_brain_evidence_available"] = evidence_available; ctx["_bitey_brain_fingerprint"] = fingerprint
        return state

    @staticmethod
    def _complexity(text: str, cognition: dict[str, Any]) -> float:
        explicit=(cognition.get("perception") or {}).get("complexity")
        if isinstance(explicit,(int,float)): return max(0,min(1,float(explicit)))
        base=.22+min(.30,len(text.split())/180); plan=cognition.get("plan") or {}
        if plan.get("needs_evidence"): base+=.12
        if plan.get("requires_specialized_module"): base+=.08
        if any(x in text.lower() for x in (" y "," además "," also "," e ",";")): base+=.05
        return min(1,base)

    @staticmethod
    def _capabilities(domain,evidence,freshness,complexity,context):
        c=["conversation"]
        if evidence:c.append("external_evidence")
        if freshness:c.append("fresh_data")
        if complexity>=.60:c.append("multi_step_reasoning")
        if domain=="research": c += ["source_comparison","research_synthesis"]
        if domain=="programming": c.append("code_reasoning")
        if domain=="trading": c.append("risk_guard")
        for x in context.get("required_capabilities") or []:
            if x not in c:c.append(str(x))
        return c
    @staticmethod
    def _tool_policy(capabilities,domain,context):
        t=[]
        if "fresh_data" in capabilities and domain=="weather":t.append("weather")
        if "external_evidence" in capabilities:
            t.append("web_research")
        if "code_reasoning" in capabilities:t.append("code_reasoning")
        if context.get("workspace_files_required"):t.append("workspace_files")
        return t
    @staticmethod
    def _objective(capabilities,domain):
        if "research_synthesis" in capabilities:return "research_and_synthesize"
        if "fresh_data" in capabilities:return "retrieve_current_data_and_answer"
        if "code_reasoning" in capabilities:return "reason_about_or_create_code"
        if domain=="trading":return "analyze_under_risk_policy"
        return "answer_or_assist"
    @staticmethod
    def _model_policy(*,domain,complexity,evidence_required,required_capabilities,verification_required):
        if "research_synthesis" in required_capabilities or complexity>=.75:return "strong_reasoning_synthesis","high_complexity_or_research"
        if verification_required or evidence_required:return "evidence_grounded_synthesis","evidence_or_verification_required"
        if "code_reasoning" in required_capabilities:return "code_reasoning","programming_capability_required"
        if domain=="trading":return "guarded_analysis","trading_risk_policy"
        return "fast_synthesis","low_complexity_direct_response"
    def system_directive(self,state):
        return ("BITEY BRAIN EXECUTIVE CONTRACT\n" f"objective={state.objective}; task={state.task_class}; mode={state.reasoning_mode}; capabilities={','.join(state.required_capabilities)}; tools={','.join(state.tool_priority) or 'none'}; model_role={state.model_role}; risk={state.risk_level}; evidence_required={state.evidence_required}; freshness_required={state.freshness_required}; verification_required={state.verification_required}.\n" "Bitey has already decided what must be done. The selected model is only an inference/synthesis worker. Do not invent facts, bypass tool/evidence requirements, or override the cognitive contract.")
    def status(self):
        return {"name":"Bitey Brain","version":"2.1.0","type":"executive_cognitive_decision_layer","provider_independent":True,"generates_language":False,"decides_before_model_selection":True,"decision_fingerprint":True,"owns":["objective","capabilities","tool_policy","evidence_policy","reasoning_policy","verification_policy","model_role_policy","risk_policy"],"external_models_are_tools":True}
