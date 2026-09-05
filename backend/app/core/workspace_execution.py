"""Bounded execution pipeline for Bitey IA Workspace tasks."""
from __future__ import annotations

from typing import Any

from .artifact_pipeline import build_artifact
from .bitey_brain import BiteyBrain
from .component_policy import validate_core_components
from .evaluation_engine import EvaluationEngine, EvaluationResult
from .multistep_runtime import MultiStepResearchRuntime
from .provider_gateway import ProviderGateway
from .task_contract import TaskContract
from .task_dag import TaskDAG, TaskNode
from .task_dag_store import dag_from_task

validate_core_components()


class WorkspaceExecutionService:
    """Bitey-owned bounded DAG runtime with durable checkpoint recovery."""
    ARTIFACT_CAPABILITIES = {"documents": "document", "slides": "presentation", "spreadsheets": "spreadsheet", "code": "code"}
    CAPABILITY_ALIASES = {"document": "documents", "documents": "documents", "doc": "documents", "presentation": "slides", "presentación": "slides", "presentacion": "slides", "slides": "slides", "spreadsheet": "spreadsheets", "spreadsheets": "spreadsheets", "hoja de cálculo": "spreadsheets", "hoja de calculo": "spreadsheets", "code": "code", "codigo": "code", "código": "code", "programa": "code", "research": "deep_research", "investigación": "deep_research", "investigacion": "deep_research"}

    def __init__(self) -> None:
        self.brain = BiteyBrain(); self.research = MultiStepResearchRuntime(max_steps=4, max_sources_per_step=5); self.providers = ProviderGateway(); self.evaluator = EvaluationEngine()

    @classmethod
    def _resolve_capability(cls, prompt: str, requested: str, state: Any) -> tuple[str, str]:
        text = prompt.lower()
        explicit = (("documents", ("documento", "document", "informe", "report", "redacta un")), ("slides", ("presentación", "presentacion", "diapositiva", "slides", "powerpoint")), ("spreadsheets", ("hoja de cálculo", "hoja de calculo", "spreadsheet", "excel", "tabla de datos")), ("code", ("código", "codigo", "programa", "script", "función", "funcion")), ("deep_research", ("investiga", "investigación", "investigacion", "deep research", "fuentes")), ("browser_research", ("busca en internet", "web actual", "información actual", "informacion actual")))
        for capability, signals in explicit:
            if any(signal in text for signal in signals): return capability, "prompt_signal"
        if state.evidence_required: return ("browser_research" if state.freshness_required else "deep_research"), "cognitive_evidence_policy"
        normalized = cls.CAPABILITY_ALIASES.get((requested or "").strip().lower())
        return (normalized, "validated_client_hint") if normalized else ("chat", "cognitive_default")

    @staticmethod
    def _needs_multistep(prompt: str, state: Any, capability: str) -> bool:
        signals = ("compara", "analiza y", "investiga y", "investigar y", "primero", "después", "despues", "luego", "crea un documento", "elabora un informe")
        return bool(state.evidence_required or float(getattr(state, "complexity", 0)) >= .65 or any(s in prompt.lower() for s in signals) or capability in {"deep_research", "browser_research"})

    def _build_dag(self, *, capability: str, state: Any, complex_task: bool) -> TaskDAG:
        artifact_type = self.ARTIFACT_CAPABILITIES.get(capability); research = bool(state.evidence_required or capability in {"deep_research", "browser_research"})
        if not complex_task: nodes = [TaskNode("worker", "worker_inference")]
        elif research and artifact_type: nodes = [TaskNode("research", "bounded_research"), TaskNode("synthesize", "compare_and_synthesize", ["research"]), TaskNode("artifact", "build_artifact", ["synthesize"]), TaskNode("evaluate", "evaluate_result", ["artifact"])]
        elif research: nodes = [TaskNode("research", "bounded_research"), TaskNode("synthesize", "synthesize", ["research"]), TaskNode("evaluate", "evaluate_result", ["synthesize"])]
        elif artifact_type: nodes = [TaskNode("worker", "worker_inference"), TaskNode("artifact", "build_artifact", ["worker"]), TaskNode("evaluate", "evaluate_result", ["artifact"])]
        else: nodes = [TaskNode("worker", "worker_inference"), TaskNode("evaluate", "evaluate_result", ["worker"])]
        dag = TaskDAG(nodes=nodes); dag.validate(); return dag

    @staticmethod
    async def _checkpoint(dag: TaskDAG, context: dict[str, Any]) -> None:
        callback = context.get("_persist_dag")
        if callback:
            result = callback(dag)
            if hasattr(result, "__await__"): await result

    @staticmethod
    def _saved(dag: TaskDAG, node_id: str) -> Any:
        try: node = dag.get(node_id)
        except ValueError: return None
        return node.result if node.status == "completed" else None

    async def execute(self, *, prompt: str, capability: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {}); requested = (capability or "chat").strip().lower(); state = self.brain.think(prompt, ctx); decision = state.as_dict()
        resolved, reason = self._resolve_capability(prompt, requested, state); complex_task = self._needs_multistep(prompt, state, resolved)
        persisted = {"metadata": ctx.get("metadata") or {}, "result": ctx.get("result") or {}}; dag = dag_from_task(persisted); resumed = dag is not None
        if dag is None: dag = self._build_dag(capability=resolved, state=state, complex_task=complex_task)
        else: dag.reset_running(); dag.validate()
        decision.update({"workspace_capability": resolved, "requested_capability": requested, "capability_resolution": reason, "execution_mode": "bounded_dag" if complex_task else "single_node", "resumed": resumed, "task_dag": dag.to_dict()}); await self._checkpoint(dag, ctx)
        contract = TaskContract(task_id=str(ctx.get("task_id") or ""), prompt=prompt, intent=str(getattr(state, "task_class", "conversation")), capability=resolved, constraints=list(getattr(state, "constraints", []) or []), risk_level=str(getattr(state, "risk_level", "low")), budget={"paid_inference": False, "max_retries": int(ctx.get("max_retries", 2))}, plan=[{"step": i, "id": n.id, "action": n.action, "depends_on": list(n.depends_on), "owner": "bitey_ia"} for i,n in enumerate(dag.nodes,1)], evidence_policy={"required": bool(state.evidence_required), "freshness": bool(state.freshness_required)}, evaluation_policy={"required": True, "decision_owner": "bitey_ia"}, artifact_contract={"type": self.ARTIFACT_CAPABILITIES.get(resolved), "required": resolved in self.ARTIFACT_CAPABILITIES} if resolved in self.ARTIFACT_CAPABILITIES else None, authorization={"side_effects": bool(getattr(state, "execution_allowed", False)), "required_for_external_actions": True}); contract.validate()
        evidence = ""; research_result = self._saved(dag, "research"); answer = self._saved(dag, "synthesize") or self._saved(dag, "worker") or ""; artifact = self._saved(dag, "artifact"); evaluation = None
        if isinstance(research_result, dict): evidence = str(research_result.get("evidence_context") or research_result.get("evidence") or "")
        saved_eval = self._saved(dag, "evaluate")
        if isinstance(saved_eval, dict) and saved_eval.get("decision"): evaluation = EvaluationResult(**{k: saved_eval.get(k) for k in ("quality","evidence_alignment","safety_compliance","contradiction_risk","confidence","decision","reasons","executive")})
        if str(getattr(state,"risk_level","low")) in {"high","critical"} and not bool(getattr(state,"execution_allowed",False)):
            answer = "Bitey no ejecutará acciones de alto impacto sin autorización explícita. La tarea queda preparada para revisión."; evaluation = self.evaluator.evaluate(user_message=prompt, answer=answer, context={"evidence_required":False,"domain":state.task_class}, evidence=evidence)
            return {"status":"needs_review","answer":answer,"cognitive_decision":decision,"task_contract":contract.to_dict(),"requested_capability":requested,"resolved_capability":resolved,"research":research_result,"evaluation":evaluation.as_dict(),"artifact":artifact,"task_dag":dag.to_dict()}
        contract.transition("planning"); await self._checkpoint(dag,ctx)
        while not dag.is_complete():
            ready = dag.ready()
            if not ready:
                raise RuntimeError("task_dag_deadlock" if dag.is_deadlocked() else "task_dag_no_ready_node")
            node = ready[0]; dag.mark_running(node.id); await self._checkpoint(dag,ctx)
            try:
                if node.action == "bounded_research":
                    contract.transition("researching"); obj = await self.research.run(prompt,ctx); research_result=obj.as_dict(); evidence=obj.evidence_context; decision={**decision,**obj.decision,"task_dag":dag.to_dict()}; dag.mark_completed(node.id,research_result)
                elif node.action in {"worker_inference","synthesize","compare_and_synthesize"}:
                    contract.transition("generating"); messages=[{"role":"system","content":self.brain.system_directive(state)},{"role":"user","content":prompt}]
                    if evidence: messages.insert(1,{"role":"system","content":"EVIDENCE CONTEXT:\n"+evidence[:18000]})
                    prior=[n.result for n in dag.nodes if n.status=="completed" and n.result]
                    if prior: messages.insert(1,{"role":"system","content":"PREVIOUS DAG RESULTS:\n"+str(prior)[-18000:]})
                    answer=await self.providers.generate(messages=messages,context={**ctx,"evidence_required":state.evidence_required,"cognition":{"intention":{"domain":state.task_class}},"task_dag":dag.to_dict()}); dag.mark_completed(node.id,answer)
                elif node.action == "build_artifact":
                    artifact_type=self.ARTIFACT_CAPABILITIES.get(resolved)
                    if not artifact_type or not answer: raise ValueError("task_dag_artifact_prerequisite_missing")
                    artifact=build_artifact(name=self._artifact_name(prompt,artifact_type),artifact_type=artifact_type,content=self._artifact_content(answer,artifact_type),metadata={"capability":resolved,"task_dag":dag.to_dict(),"owner":"bitey_ia"}); dag.mark_completed(node.id,artifact)
                elif node.action == "evaluate_result":
                    contract.transition("evaluating"); evaluation=self.evaluator.evaluate(user_message=prompt,answer=answer,context={**ctx,"evidence_required":state.evidence_required,"domain":state.task_class},evidence=evidence); dag.mark_completed(node.id,evaluation.as_dict())
                else: raise ValueError(f"task_dag_unknown_action:{node.action}")
            except Exception as exc:
                dag.mark_failed(node.id,{"error":type(exc).__name__}); await self._checkpoint(dag,ctx); raise
            decision["task_dag"]=dag.to_dict(); await self._checkpoint(dag,ctx)
        if evaluation is None: evaluation=self.evaluator.evaluate(user_message=prompt,answer=answer,context={**ctx,"evidence_required":state.evidence_required,"domain":state.task_class},evidence=evidence)
        final="completed" if evaluation.decision=="accept" else "needs_review"; contract.transition(final,reason=None if final=="completed" else "evaluation_requires_review"); decision["task_dag"]=dag.to_dict()
        return {"status":final,"answer":answer,"cognitive_decision":decision,"task_contract":contract.to_dict(),"requested_capability":requested,"resolved_capability":resolved,"research":research_result,"evaluation":evaluation.as_dict(),"artifact":artifact,"task_dag":dag.to_dict()}

    @staticmethod
    def _artifact_name(prompt: str, artifact_type: str) -> str:
        title=" ".join(prompt.strip().split())[:70] or "Nuevo artefacto"; suffix={"document":"Documento","presentation":"Presentación","spreadsheet":"Hoja de cálculo","code":"Código"}.get(artifact_type,"Artefacto"); return f"{title} — {suffix}"

    @staticmethod
    def _artifact_content(answer: str, artifact_type: str) -> Any:
        if artifact_type == "spreadsheet": return {"format":"table-ready","content":answer}
        if artifact_type == "presentation": return {"format":"slide-ready","content":answer}
        if artifact_type == "code": return {"format":"source-ready","content":answer}
        return {"format":"markdown","content":answer}
