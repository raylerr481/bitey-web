"""Bounded execution pipeline for Bitey IA Workspace tasks."""
from __future__ import annotations

from typing import Any

from .artifact_pipeline import build_artifact
from .bitey_brain import BiteyBrain
from .component_policy import validate_core_components
from .evaluation_engine import EvaluationEngine
from .multistep_runtime import MultiStepResearchRuntime
from .provider_gateway import ProviderGateway
from .task_contract import TaskContract
from .task_dag import TaskDAG, TaskNode

validate_core_components()


class WorkspaceExecutionService:
    """Connect executive cognition, a bounded DAG, workers and evaluation."""

    ARTIFACT_CAPABILITIES = {"documents": "document", "slides": "presentation", "spreadsheets": "spreadsheet", "code": "code"}
    CAPABILITY_ALIASES = {
        "document": "documents", "documents": "documents", "doc": "documents",
        "presentation": "slides", "presentación": "slides", "presentacion": "slides", "slides": "slides",
        "spreadsheet": "spreadsheets", "spreadsheets": "spreadsheets", "hoja de cálculo": "spreadsheets", "hoja de calculo": "spreadsheets",
        "code": "code", "codigo": "code", "código": "code", "programa": "code",
        "research": "deep_research", "investigación": "deep_research", "investigacion": "deep_research",
    }

    def __init__(self) -> None:
        self.brain = BiteyBrain()
        self.research = MultiStepResearchRuntime(max_steps=4, max_sources_per_step=5)
        self.providers = ProviderGateway()
        self.evaluator = EvaluationEngine()

    @classmethod
    def _resolve_capability(cls, prompt: str, requested: str, state: Any) -> tuple[str, str]:
        text = prompt.lower()
        explicit = (
            ("documents", ("documento", "document", "informe", "report", "redacta un")),
            ("slides", ("presentación", "presentacion", "diapositiva", "slides", "powerpoint")),
            ("spreadsheets", ("hoja de cálculo", "hoja de calculo", "spreadsheet", "excel", "tabla de datos")),
            ("code", ("código", "codigo", "programa", "script", "función", "funcion")),
            ("deep_research", ("investiga", "investigación", "investigacion", "deep research", "fuentes")),
            ("browser_research", ("busca en internet", "web actual", "información actual", "informacion actual")),
        )
        for capability, signals in explicit:
            if any(signal in text for signal in signals):
                return capability, "prompt_signal"
        if state.evidence_required:
            return ("browser_research" if state.freshness_required else "deep_research"), "cognitive_evidence_policy"
        normalized = cls.CAPABILITY_ALIASES.get((requested or "").strip().lower())
        if normalized:
            return normalized, "validated_client_hint"
        return "chat", "cognitive_default"

    @staticmethod
    def _needs_multistep(prompt: str, state: Any, resolved_capability: str) -> bool:
        text = prompt.lower()
        signals = ("compara", "compara y", "analiza y", "investiga y", "investigar y", "primero", "después", "despues", "luego", "crea un documento", "elabora un informe")
        return bool(state.evidence_required or float(getattr(state, "complexity", 0.0)) >= 0.65 or any(s in text for s in signals) or resolved_capability in {"deep_research", "browser_research"})

    def _build_dag(self, *, prompt: str, resolved_capability: str, state: Any, complex_task: bool) -> TaskDAG:
        artifact_type = self.ARTIFACT_CAPABILITIES.get(resolved_capability)
        needs_research = bool(state.evidence_required or resolved_capability in {"deep_research", "browser_research"})
        if not complex_task:
            nodes = [TaskNode("worker", "worker_inference")]
        elif needs_research and artifact_type:
            nodes = [
                TaskNode("research", "bounded_research"),
                TaskNode("synthesize", "compare_and_synthesize", ["research"]),
                TaskNode("artifact", "build_artifact", ["synthesize"]),
                TaskNode("evaluate", "evaluate_result", ["artifact"]),
            ]
        elif needs_research:
            nodes = [
                TaskNode("research", "bounded_research"),
                TaskNode("synthesize", "synthesize", ["research"]),
                TaskNode("evaluate", "evaluate_result", ["synthesize"]),
            ]
        elif artifact_type:
            nodes = [TaskNode("worker", "worker_inference"), TaskNode("artifact", "build_artifact", ["worker"]), TaskNode("evaluate", "evaluate_result", ["artifact"])]
        else:
            nodes = [TaskNode("worker", "worker_inference"), TaskNode("evaluate", "evaluate_result", ["worker"])]
        dag = TaskDAG(nodes=nodes)
        dag.validate()
        return dag

    def _build_contract(self, *, prompt: str, requested_capability: str, resolved_capability: str, state: Any, decision: dict[str, Any], context: dict[str, Any], dag: TaskDAG) -> TaskContract:
        artifact_type = self.ARTIFACT_CAPABILITIES.get(resolved_capability)
        contract = TaskContract(
            prompt=prompt,
            intent=str(getattr(state, "task_class", "conversation")),
            capability=resolved_capability,
            constraints=list(getattr(state, "constraints", []) or []),
            risk_level=str(getattr(state, "risk_level", "low")),
            budget={"paid_inference": False, "max_retries": int(context.get("max_retries", 2))},
            plan=[{"step": index, "id": node.id, "action": node.action, "depends_on": list(node.depends_on), "owner": "bitey_ia"} for index, node in enumerate(dag.nodes, 1)],
            evidence_policy={"required": bool(getattr(state, "evidence_required", False)), "freshness": bool(getattr(state, "freshness_required", False))},
            evaluation_policy={"required": True, "decision_owner": "bitey_ia"},
            artifact_contract={"type": artifact_type, "required": bool(artifact_type)} if artifact_type else None,
            authorization={"side_effects": bool(getattr(state, "execution_allowed", False)), "required_for_external_actions": True},
        )
        contract.validate()
        return contract

    async def execute(self, *, prompt: str, capability: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {})
        requested_capability = (capability or "chat").strip().lower()
        state = self.brain.think(prompt, ctx)
        decision = state.as_dict()
        resolved_capability, resolution_reason = self._resolve_capability(prompt, requested_capability, state)
        complex_task = self._needs_multistep(prompt, state, resolved_capability)
        dag = self._build_dag(prompt=prompt, resolved_capability=resolved_capability, state=state, complex_task=complex_task)
        decision.update({"workspace_capability": resolved_capability, "requested_capability": requested_capability, "capability_resolution": resolution_reason, "execution_mode": "bounded_dag" if complex_task else "single_node", "task_dag": dag.to_dict()})
        contract = self._build_contract(prompt=prompt, requested_capability=requested_capability, resolved_capability=resolved_capability, state=state, decision=decision, context=ctx, dag=dag)

        evidence = ""
        research_result: dict[str, Any] | None = None
        answer = ""
        artifact = None
        evaluation = None

        contract.transition("planning")
        while True:
            ready = dag.ready()
            if not ready:
                break
            node = ready[0]
            if node.action == "bounded_research":
                contract.transition("researching")
                result_obj = await self.research.run(prompt, ctx)
                research_result = result_obj.as_dict()
                evidence = result_obj.evidence_context
                decision = {**decision, **result_obj.decision, "task_dag": dag.to_dict()}
                dag.mark_completed(node.id, research_result)
            elif node.action in {"worker_inference", "synthesize", "compare_and_synthesize"}:
                contract.transition("generating")
                messages = [{"role": "system", "content": self.brain.system_directive(state)}, {"role": "user", "content": prompt}]
                if evidence:
                    messages.insert(1, {"role": "system", "content": "EVIDENCE CONTEXT:\n" + evidence[:18000]})
                prior = [n.result for n in dag.nodes if n.status == "completed" and n.result]
                if prior:
                    messages.insert(1, {"role": "system", "content": "PREVIOUS DAG RESULTS:\n" + str(prior)[-18000:]})
                answer = await self.providers.generate(messages=messages, context={**ctx, "evidence_required": state.evidence_required, "cognition": {"intention": {"domain": state.task_class}}, "task_dag": dag.to_dict()})
                dag.mark_completed(node.id, answer)
            elif node.action == "build_artifact":
                artifact_type = self.ARTIFACT_CAPABILITIES.get(resolved_capability)
                if not artifact_type or not answer:
                    raise ValueError("task_dag_artifact_prerequisite_missing")
                artifact = build_artifact(name=self._artifact_name(prompt, artifact_type), artifact_type=artifact_type, content=self._artifact_content(answer, artifact_type), metadata={"capability": resolved_capability, "task_dag": dag.to_dict(), "owner": "bitey_ia"})
                dag.mark_completed(node.id, artifact)
            elif node.action == "evaluate_result":
                contract.transition("evaluating")
                evaluation = self.evaluator.evaluate(user_message=prompt, answer=answer, context={**ctx, "evidence_required": state.evidence_required, "domain": state.task_class}, evidence=evidence)
                dag.mark_completed(node.id, evaluation.as_dict())
            else:
                raise ValueError(f"task_dag_unknown_action:{node.action}")
            decision["task_dag"] = dag.to_dict()

        if evaluation is None:
            contract.transition("evaluating")
            evaluation = self.evaluator.evaluate(user_message=prompt, answer=answer, context={**ctx, "evidence_required": state.evidence_required, "domain": state.task_class}, evidence=evidence)
        final_status = "completed" if evaluation.decision == "accept" else "needs_review"
        contract.transition(final_status, reason=None if final_status == "completed" else "evaluation_requires_review")
        decision["task_dag"] = dag.to_dict()
        return {"status": final_status, "answer": answer, "cognitive_decision": decision, "task_contract": contract.to_dict(), "requested_capability": requested_capability, "resolved_capability": resolved_capability, "research": research_result, "evaluation": evaluation.as_dict(), "artifact": artifact, "task_dag": dag.to_dict()}

    @staticmethod
    def _artifact_name(prompt: str, artifact_type: str) -> str:
        title = " ".join(prompt.strip().split())[:70] or "Nuevo artefacto"
        suffix = {"document": "Documento", "presentation": "Presentación", "spreadsheet": "Hoja de cálculo", "code": "Código"}.get(artifact_type, "Artefacto")
        return f"{title} — {suffix}"

    @staticmethod
    def _artifact_content(answer: str, artifact_type: str) -> Any:
        if artifact_type == "spreadsheet": return {"format": "table-ready", "content": answer}
        if artifact_type == "presentation": return {"format": "slide-ready", "content": answer}
        if artifact_type == "code": return {"format": "source-ready", "content": answer}
        return {"format": "markdown", "content": answer}
