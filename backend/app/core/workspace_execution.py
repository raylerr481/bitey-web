"""Bounded execution pipeline for Bitey IA Workspace tasks."""
from __future__ import annotations

from typing import Any

from .artifact_engine import ArtifactEngine
from .bitey_brain import BiteyBrain
from .evaluation_engine import EvaluationEngine
from .multistep_runtime import MultiStepResearchRuntime
from .provider_gateway import ProviderGateway


class WorkspaceExecutionService:
    """Connect executive cognition, research, generation and evaluation."""

    ARTIFACT_CAPABILITIES = {"documents": "document", "slides": "presentation", "spreadsheets": "spreadsheet", "code": "code"}

    def __init__(self) -> None:
        self.brain = BiteyBrain()
        self.research = MultiStepResearchRuntime(max_steps=4, max_sources_per_step=5)
        self.providers = ProviderGateway()
        self.evaluator = EvaluationEngine()
        self.artifacts = ArtifactEngine()

    @staticmethod
    def _artifact_authorized(state: Any, evaluation: Any, artifact_type: str | None) -> bool:
        if not artifact_type or not bool(getattr(state, "execution_allowed", False)):
            return False
        if getattr(state, "risk_level", "low") in {"high", "critical"}:
            return False
        return getattr(evaluation, "decision", "reject") == "accept"

    async def execute(self, *, prompt: str, capability: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {})
        trace: list[dict[str, Any]] = []

        def phase(name: str, status: str = "completed", detail: str | None = None) -> None:
            item = {"phase": name, "status": status}
            if detail:
                item["detail"] = detail
            trace.append(item)

        phase("thinking", "running", "Bitey Brain analiza la solicitud")
        state = self.brain.think(prompt, ctx)
        decision = state.as_dict()
        trace[-1]["status"] = "completed"
        phase("planning", "completed", state.reasoning_mode)

        evidence = ""
        research_result = None
        if capability in {"deep_research", "browser_research"} or state.evidence_required:
            phase("researching", "running", "Investigación acotada")
            research_result_obj = await self.research.run(prompt, ctx)
            research_result = research_result_obj.as_dict()
            evidence = research_result_obj.evidence_context
            decision = research_result_obj.decision
            trace[-1]["status"] = "completed"
        else:
            phase("researching", "skipped", "No se requiere evidencia externa")

        phase("generating", "running")
        if state.risk_level in {"high", "critical"} and not state.execution_allowed:
            answer = "Bitey no ejecutará una acción de alto impacto. Puedo analizarla, preparar un plan o generar un borrador seguro para revisión humana."
            trace[-1]["status"] = "completed"
            trace[-1]["detail"] = "Generación segura sin ejecución de alto impacto"
        else:
            messages = [{"role": "system", "content": self.brain.system_directive(state)}, {"role": "user", "content": prompt}]
            if evidence:
                messages.insert(1, {"role": "system", "content": "EVIDENCE CONTEXT:\n" + evidence[:18000]})
            answer = await self.providers.generate(messages=messages, context={**ctx, "evidence_required": state.evidence_required, "cognition": {"intention": {"domain": state.task_class}}})
            trace[-1]["status"] = "completed"

        phase("evaluating", "running")
        evaluation = self.evaluator.evaluate(user_message=prompt, answer=answer, context={**ctx, "evidence_required": state.evidence_required, "domain": state.task_class}, evidence=evidence)
        trace[-1]["status"] = "completed"
        trace[-1]["detail"] = evaluation.decision

        artifact_type = self.ARTIFACT_CAPABILITIES.get(capability)
        artifact_authorized = self._artifact_authorized(state, evaluation, artifact_type)
        artifact = None
        if artifact_authorized:
            phase("artifact", "running", artifact_type)
            artifact_obj = self.artifacts.build(
                prompt=prompt,
                answer=answer,
                artifact_type=artifact_type,
                metadata={"capability": capability, "evaluation": evaluation.as_dict(), "cognitive_decision": decision, "evidence_present": bool(evidence), "authorization": "bitey_brain_bounded_gate"},
            )
            artifact = artifact_obj.as_dict()
            trace[-1]["status"] = "completed"
        elif artifact_type:
            phase("artifact", "blocked", "Bitey Brain gate or evaluation did not authorize artifact creation")

        phase("ready", "completed")
        return {"status": "completed" if evaluation.decision == "accept" else "needs_review", "answer": answer, "cognitive_decision": decision, "research": research_result, "evaluation": evaluation.as_dict(), "artifact": artifact, "artifact_authorized": artifact_authorized, "execution_trace": trace}
