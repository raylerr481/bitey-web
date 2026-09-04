"""Bounded orchestration for Bitey IA multi-deliverable workspace tasks."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .multistep_runtime import MultiStepResearchRuntime
from .workspace_execution import WorkspaceExecutionService

@dataclass(frozen=True)
class Deliverable:
    capability: str
    artifact_type: str
    reason: str

class WorkspaceOrchestrator:
    """Plan and coordinate a bounded set of deliverables without duplicating research."""
    MAX_DELIVERABLES=4
    KEYWORDS={
        "document":("document","docx","informe","report","documento","pdf"),
        "presentation":("presentation","slides","ppt","pptx","presentación","diapositivas"),
        "spreadsheet":("spreadsheet","excel","xlsx","csv","hoja","tabla","datos"),
        "code":("code","codigo","código","programa","script","developer"),
    }
    RESEARCH_HINTS=("investiga","investigación","research","fuentes","evidencia","mercado","análisis","analisis")
    def __init__(self,execution:WorkspaceExecutionService|None=None)->None:
        self.execution=execution or WorkspaceExecutionService(); self.research=MultiStepResearchRuntime(max_steps=4,max_sources_per_step=5)
    def plan(self,prompt:str,requested_capability:str="chat")->list[Deliverable]:
        text=prompt.lower(); found=[]
        for artifact_type,words in self.KEYWORDS.items():
            if any(w in text for w in words):
                capability=next((k for k,v in self.execution.ARTIFACT_CAPABILITIES.items() if v==artifact_type),artifact_type); found.append(Deliverable(capability,artifact_type,"requested_or_detected_from_prompt"))
        if not found and requested_capability in self.execution.ARTIFACT_CAPABILITIES:
            found.append(Deliverable(requested_capability,self.execution.ARTIFACT_CAPABILITIES[requested_capability],"explicit_capability"))
        return found[:self.MAX_DELIVERABLES]
    async def execute(self,*,prompt:str,capability:str="chat",context:dict[str,Any]|None=None)->dict[str,Any]:
        ctx=dict(context or {}); deliverables=self.plan(prompt,capability)
        if not deliverables:return await self.execution.execute(prompt=prompt,capability=capability,context=ctx)
        shared=None
        if len(deliverables)>1 and (ctx.get("force_research") or any(x in prompt.lower() for x in self.RESEARCH_HINTS)):
            rr=await self.research.run(prompt,ctx); shared={"result":rr.as_dict(),"evidence_context":rr.evidence_context}
        results=[]
        for item in deliverables:
            c={**ctx,"orchestration":{"artifact_type":item.artifact_type,"reason":item.reason}}
            if shared:c["shared_research"]=shared
            result=await self.execution.execute(prompt=prompt,capability=item.capability,context=c)
            results.append({"capability":item.capability,"artifact_type":item.artifact_type,"result":result})
            if result.get("status") not in {"completed","needs_review"}:break
        accepted=sum(1 for x in results if x["result"].get("status")=="completed")
        return {"status":"completed" if accepted==len(results) and results else "needs_review","orchestrated":True,"deliverable_count":len(deliverables),"completed_count":accepted,"research_shared":bool(shared),"deliverables":results,"execution_policy":{"max_deliverables":self.MAX_DELIVERABLES,"sequential":True,"shared_research":bool(shared),"side_effects":"delegated_to_workspace_execution_gate"}}
