"""Bounded execution pipeline for Bitey IA Workspace tasks."""
from __future__ import annotations

from typing import Any

from .artifact_pipeline import build_artifact
from .bitey_brain import BiteyBrain
from .component_policy import validate_core_components
from .evaluation_engine import EvaluationEngine
from .multistep_runtime import MultiStepResearchRuntime
from .provider_gateway import ProviderGateway

validate_core_components()


class WorkspaceExecutionService:
    """Connect executive cognition, bounded research, workers and evaluation."""

    ARTIFACT_CAPABILITIES = {
        "documents": "document",
        "slides": "presentation",
        "spreadsheets": "spreadsheet",
        "code": "code",
    }

    def __init__(self) -> None:
        self.brain = BiteyBrain()
        self.research = MultiStepResearchRuntime(max_steps=4, max_sources_per_step=5)
        self.providers = ProviderGateway()
        self.evaluator = EvaluationEngine()

    async def execute(self, *, prompt: str, capability: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {})
        state = self.brain.think(prompt, ctx)
        decision = state.as_dict()
        evidence = ""
        research_result: dict[str, Any] | None = None

        if capability in {"deep_research", "browser_research"} or state.evidence_required:
            research_result_obj = await self.research.run(prompt, ctx)
            research_result = research_result_obj.as_dict()
            evidence = research_result_obj.evidence_context
            decision = research_result_obj.decision

        if state.risk_level in {"high", "critical"} and not state.execution_allowed:
            answer = "Bitey no ejecutará una acción de alto impacto. Puedo analizarla, preparar un plan o generar un borrador seguro para revisión humana."
        else:
            messages = [
                {"role": "system", "content": self.brain.system_directive(state)},
                {"role": "user", "content": prompt},
            ]
            if evidence:
                messages.insert(1, {"role": "system", "content": "EVIDENCE CONTEXT:\n" + evidence[:18000]})
            answer = await self.providers.generate(
                messages=messages,
                context={**ctx, "evidence_required": state.evidence_required, "cognition": {"intention": {"domain": state.task_class}}},
            )

        evaluation = self.evaluator.evaluate(
            user_message=prompt,
            answer=answer,
            context={**ctx, "evidence_required": state.evidence_required, "domain": state.task_class},
            evidence=evidence,
        )

        artifact_type = self.ARTIFACT_CAPABILITIES.get(capability)
        artifact = None
        if artifact_type and evaluation.decision == "accept":
            content = self._artifact_content(answer, artifact_type)
            artifact = build_artifact(
                name=self._artifact_name(prompt, artifact_type),
                artifact_type=artifact_type,
                content=content,
                metadata={
                    "capability": capability,
                    "evaluation": evaluation.as_dict(),
                    "cognitive_decision": decision,
                    "evidence_present": bool(evidence),
                    "owner": "bitey_ia",
                },
            )

        return {
            "status": "completed" if evaluation.decision == "accept" else "needs_review",
            "answer": answer,
            "cognitive_decision": decision,
            "research": research_result,
            "evaluation": evaluation.as_dict(),
            "artifact": artifact,
        }

    @staticmethod
    def _artifact_name(prompt: str, artifact_type: str) -> str:
        title = " ".join(prompt.strip().split())[:70] or "Nuevo artefacto"
        suffix = {"document": "Documento", "presentation": "Presentación", "spreadsheet": "Hoja de cálculo", "code": "Código"}.get(artifact_type, "Artefacto")
        return f"{title} — {suffix}"

    @staticmethod
    def _artifact_content(answer: str, artifact_type: str) -> Any:
        if artifact_type == "spreadsheet":
            return {"format": "table-ready", "content": answer}
        if artifact_type == "presentation":
            return {"format": "slide-ready", "content": answer}
        if artifact_type == "code":
            return {"format": "source-ready", "content": answer}
        return {"format": "markdown", "content": answer}
