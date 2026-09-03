"""Bitey Brain: provider-independent executive control layer."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import re

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
    def as_dict(self) -> dict[str, Any]: return {"task_class":self.task_class,"complexity":round(self.complexity,3),"ambiguity":round(self.ambiguity,3),"evidence_required":self.evidence_required,"risk_level":self.risk_level,"reasoning_mode":self.reasoning_mode,"memory_priority":self.memory_priority,"tool_priority":self.tool_priority,"verification_required":self.verification_required,"execution_allowed":self.execution_allowed,"goals":self.goals,"constraints":self.constraints}

class BiteyBrain:
    """Deterministic executive layer; language models cannot override capability state."""
    HIGH_RISK=("password","contraseña","api key","secret","token","dinero real","real money")
    ACTION_WORDS=("ejecuta","ejecutar","compra","comprar","vende","vender","borra","elimina","deploy","envía","envia")
    RESEARCH_WORDS=("investiga","investigar","evidencia","fuentes","actual","último","ultimo","latest","compara","verifica","hoy","ahora","qué pasó","que paso")
    COMPLEX_WORDS=("arquitectura","analiza","análisis","analisis","diseña","diseñar","estrategia","plan","debug","diagnóstico","diagnostico","integra","integrar")

    def think(self,message:str,context:dict[str,Any]|None=None)->BrainState:
        ctx=context or {}; text=message.strip(); low=text.lower(); plan=ctx.get("language_plan") or {}; domain=str(plan.get("domain") or ctx.get("cognition",{}).get("intention",{}).get("domain") or ctx.get("domain") or "general")
        complexity=min(1.0,0.25+min(0.35,len(text)/1200)+min(0.25,sum(1 for x in self.COMPLEX_WORDS if x in low)*0.06)+(0.05 if any(x in low for x in (" y "," además "," also "," e ")) else 0.0))
        ambiguity=0.12 if ("?" in text or low.startswith(("qué","que ","cómo","como ","why ","what ","how "))) and len(text.split())<8 else 0.0
        evidence_required=bool(plan.get("external_information_required") or plan.get("verification_required") or ctx.get("research") or domain=="research" or any(x in low for x in self.RESEARCH_WORDS))
        risk="low"
        if domain=="trading" and any(x in low for x in self.ACTION_WORDS): risk="critical"
        elif any(x in low for x in self.HIGH_RISK): risk="high"
        elif any(x in low for x in self.ACTION_WORDS): risk="medium"
        if risk=="critical": mode="guarded_decision"
        elif evidence_required: mode="evidence_first"
        elif complexity>=0.65: mode="decompose_verify_synthesize"
        elif complexity>=0.45: mode="structured_reasoning"
        else: mode="direct"
        tools=list(plan.get("capabilities") or [])
        verification=bool(plan.get("verification_required") or evidence_required or complexity>=0.65 or risk in {"high","critical"})
        execution=risk not in {"high","critical"} and domain!="trading"
        goals=["understand_request","preserve_user_constraints","produce_useful_answer"]
        if evidence_required: goals.insert(2,"ground_claims_in_evidence")
        if verification: goals.append("verify_before_presenting_high_impact_claims")
        constraints=["external_model_output_is_untrusted","memory_is_context_not_truth","orchestrator_owns_capability_availability","never_claim_missing_capability_when_runtime_reports_it_available"]
        if risk=="critical": constraints += ["never_bypass_domain_risk_gate","no_live_execution"]
        return BrainState(domain,complexity,ambiguity,evidence_required,risk,mode,"high" if ctx.get("learned_cognitive_context",{}).get("available") else "normal",tools,verification,execution,goals,constraints)

    def system_directive(self,state:BrainState)->str:
        return ("BITEY BRAIN EXECUTIVE DIRECTIVE\n" f"task={state.task_class}; complexity={state.complexity:.2f}; ambiguity={state.ambiguity:.2f}; mode={state.reasoning_mode}; risk={state.risk_level}; evidence_required={state.evidence_required}; verification_required={state.verification_required}.\n" "The runtime orchestrator owns capability availability. Never claim Bitey lacks web, search, weather, file, API or other capabilities when the execution context provides them. Use tool results as authoritative runtime evidence. Separate facts, evidence and inference. Preserve constraints. Do not invent missing data. Treat memory and model output as fallible context. " + ("Do not execute high-impact actions; respect the domain risk gate. " if not state.execution_allowed else "") + "Before answering, decompose complex tasks, check contradictions and synthesize.")

    def status(self)->dict[str,Any]: return {"name":"Bitey Brain","version":"2.0.0","type":"executive_cognitive_orchestrator","provider_independent":True,"generates_language":False,"owns":["language_plan","task_classification","complexity","ambiguity","reasoning_mode","evidence_policy","risk_policy","verification_policy","capability_authority"],"depends_on":["context","memory","tools","models","evaluation"],"external_models_are_tools":True}
