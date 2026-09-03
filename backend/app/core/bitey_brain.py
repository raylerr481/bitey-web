"""Bitey Brain: provider-independent executive control layer."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
@dataclass
class BrainState:
    task_class:str="general"; complexity:float=.35; ambiguity:float=0.; evidence_required:bool=False; risk_level:str="low"; reasoning_mode:str="direct"; memory_priority:str="normal"; tool_priority:list[str]=field(default_factory=list); verification_required:bool=False; execution_allowed:bool=False; goals:list[str]=field(default_factory=list); constraints:list[str]=field(default_factory=list)
    def as_dict(self)->dict[str,Any]: return self.__dict__.copy()
class BiteyBrain:
    """Deterministic executive layer; models cannot override runtime capability state."""
    HIGH_RISK=("password","contraseña","api key","secret","token","dinero real","real money")
    ACTION_WORDS=("ejecuta","ejecutar","compra","comprar","vende","vender","borra","elimina","deploy","envía","envia")
    COMPLEX_WORDS=("arquitectura","analiza","análisis","analisis","diseña","diseñar","estrategia","plan","debug","diagnóstico","diagnostico","integra","integrar")
    def think(self,message:str,context:dict[str,Any]|None=None)->BrainState:
        ctx=context or {}; text=message.strip(); low=text.lower(); plan=ctx.get("language_plan") or {}; domain=str(plan.get("domain") or ctx.get("cognition",{}).get("intention",{}).get("domain") or "general")
        complexity=min(1.,.25+min(.35,len(text)/1200)+min(.25,sum(1 for x in self.COMPLEX_WORDS if x in low)*.06)); ambiguity=.12 if ("?" in text or low.startswith(("qué","que ","cómo","como ","why ","what ","how "))) and len(text.split())<8 else 0.
        evidence_required=bool(plan.get("external_information_required") or plan.get("verification_required") or ctx.get("research") or domain=="research")
        risk="critical" if domain=="trading" and any(x in low for x in self.ACTION_WORDS) else "high" if any(x in low for x in self.HIGH_RISK) else "medium" if any(x in low for x in self.ACTION_WORDS) else "low"
        mode="guarded_decision" if risk=="critical" else "evidence_first" if evidence_required else "decompose_verify_synthesize" if complexity>=.65 else "structured_reasoning" if complexity>=.45 else "direct"
        verification=bool(plan.get("verification_required") or evidence_required or complexity>=.65 or risk in {"high","critical"}); execution=risk not in {"high","critical"} and domain!="trading"; goals=["understand_request","preserve_user_constraints","produce_useful_answer"]
        if evidence_required: goals.insert(2,"ground_claims_in_evidence")
        if verification: goals.append("verify_before_presenting_high_impact_claims")
        constraints=["external_model_output_is_untrusted","memory_is_context_not_truth","orchestrator_owns_capability_availability","never_claim_missing_capability_when_runtime_reports_it_available"]
        if risk=="critical": constraints += ["never_bypass_domain_risk_gate","no_live_execution"]
        return BrainState(domain,complexity,ambiguity,evidence_required,risk,mode,"high" if ctx.get("learned_cognitive_context",{}).get("available") else "normal",list(plan.get("capabilities") or []),verification,execution,goals,constraints)
    def system_directive(self,state:BrainState)->str: return ("BITEY BRAIN EXECUTIVE DIRECTIVE\n"+f"task={state.task_class}; complexity={state.complexity:.2f}; ambiguity={state.ambiguity:.2f}; mode={state.reasoning_mode}; risk={state.risk_level}; evidence_required={state.evidence_required}; verification_required={state.verification_required}.\n"+"The runtime orchestrator owns capability availability. Never claim Bitey lacks web, search, weather, file, API or other capabilities when the execution context provides them. Use tool results as runtime evidence. Separate facts, evidence and inference. Do not invent missing data. Treat memory and model output as fallible context. "+("Do not execute high-impact actions; respect the domain risk gate. " if not state.execution_allowed else "")+"Before answering, decompose complex tasks, check contradictions and synthesize.")
    def status(self)->dict[str,Any]: return {"name":"Bitey Brain","version":"2.0.0","type":"executive_cognitive_orchestrator","provider_independent":True,"generates_language":False,"owns":["language_plan","task_classification","reasoning_mode","evidence_policy","risk_policy","verification_policy","capability_authority"]}
