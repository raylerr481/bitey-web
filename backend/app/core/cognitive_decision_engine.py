from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class CognitiveDecision:
    action: str
    confidence: float
    reasons: tuple[str, ...]
    def as_dict(self) -> dict[str, Any]: return asdict(self)

class CognitiveDecisionEngine:
    ACTIONS=("ANSWER","SEARCH_MORE","CHANGE_QUERY","USE_ANOTHER_SOURCE","ASK_USER","REFUSE")
    def decide(self, *, evidence_count:int=0, evidence_score:float=0.0, contradiction:bool=False, capability_available:bool=True, high_risk:bool=False, user_ambiguity:bool=False)->CognitiveDecision:
        if high_risk: return CognitiveDecision("REFUSE",0.99,("risk_policy",))
        if user_ambiguity and evidence_count==0: return CognitiveDecision("ASK_USER",0.90,("insufficient_task_definition",))
        if not capability_available: return CognitiveDecision("ASK_USER",0.88,("required_capability_unavailable",))
        if contradiction: return CognitiveDecision("SEARCH_MORE",0.93,("contradictory_evidence","independent_verification_required"))
        if evidence_count==0: return CognitiveDecision("SEARCH_MORE",0.82,("no_evidence",))
        if evidence_score<0.30: return CognitiveDecision("CHANGE_QUERY",0.80,("weak_evidence","query_refinement_required"))
        if evidence_score<0.55: return CognitiveDecision("USE_ANOTHER_SOURCE",0.76,("partial_evidence","source_diversification_required"))
        return CognitiveDecision("ANSWER",min(0.99,0.55+evidence_score*0.44),("evidence_sufficient",))
