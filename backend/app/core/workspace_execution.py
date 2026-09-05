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

validate_core_components()


class WorkspaceExecutionService:
    """Connect executive cognition, bounded research, workers and evaluation."""

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

    def _build_contract(self, *, prompt: str, requested_capability: str, resolved_capability: str, state: Any, decision: dict[str, Any], context: dict[str, Any]) -> TaskContract:
        artifact_type = self.ARTIFACT_CAPABILITIES.get(resolved_capability)
        contract = TaskContract(
            prompt=prompt,
            intent=str(getattr(state, "task_class", "conversation")),
            capability=resolved_capability,
            constraints=list(getattr(state, "constraints", []) or []),
            risk_level=str(getattr(state, "risk_level", "low")),
            budget={"paid_inference": False, "max_retries": int(context.get("max_retries", 2))},
            plan=[{"step": 1, "action": "cognitive_decision", "owner": "bitey_ia"}],
            evidence_policy={"required": bool(getattr(state, "evidence_required", False)), "freshness": bool(getattr(state, "freshness_required", False))},
            evaluation_policy={"required": True, "decision_owner": "bitey_ia"},
            artifact_contract={"type": artifact_type, "required": bool(artifact_type)} if artifact_type else None,
            authorization={"side_effects": bool(getattr(state, "execution_allowed", False)), "required_for_external_actions": True},
        )
        contract.plan.append({"step": 2, "action": "resolve_capability", "requested": requested_capability, "resolved": resolved_capability})
        contract.plan.append({"step": 3, "action": "research_if_required", "bounded": True, "max_steps": 4})
        contract.plan.append({"step": 4, "action": "worker_inference", "paid_forbidden": True})
        contract.plan.append({"step": 5, "action": "evaluation", "required": True})
        contract.validate()
        return contract

    async def execute(self, *, prompt: str, capability: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {})
        requested_capability = (capability or "chat").strip().lower()
        state = self.brain.think(prompt, ctx)
        decision = state.as_dict()
        resolved_capability, resolution_reason = self._resolve_capability(prompt, requested_capability, state)
        decision.update({"workspace_capability": resolved_capability, "requested_capability": requested_capability, "capability_resolution": resolution_reason})
        contract = self._build_contract(prompt=prompt, requested_capability=requested_capability, resolved_capability=resolved_capability, state=state, decision=decision, context=ctx)
        evidence = ""
        research_result: dict[str, Any] | None = None

        if resolved_capability in {"deep_research", "browser_research"} or state.evidence_required:
            contract.transition("researching")
            contract.plan.append({"step": 6, "action": "bounded_research", "max_steps": 4, "max_sources_per_step": 5})
            research_result_obj = await self.research.run(prompt, ctx)
            research_result = research_result_obj.as_dict()
            evidence = research_result_obj.evidence_context
            decision = {**decision, **research_result_obj.decision, "workspace_capability": resolved_capability, "requested_capability": requested_capability, "capability_resolution": resolution_reason}

        if state.risk_level in {"high", "critical"} and not state.execution_allowed:
            answer = "Bitey no ejecutará una acción de alto impacto. Puedo analizarla, preparar un plan o generar un borrador seguro para revisión humana."
        else:
            contract.transition("generating")
            messages = [{"role": "system", "content": self.brain.system_directive(state)}, {"role": "user", "content": prompt}]
            if evidence:
                messages.insert(1, {"role": "system", "content": "EVIDENCE CONTEXT:\n" + evidence[:18000]})
            answer = await self.providers.generate(messages=messages, context={**ctx, "evidence_required": state.evidence_required, "cognition": {"intention": {"domain": state.task_class}}})

        contract.transition("evaluating")
        evaluation = self.evaluator.evaluate(user_message=prompt, answer=answer, context={**ctx, "evidence_required": state.evidence_required, "domain": state.task_class}, evidence=evidence)
        artifact_type = self.ARTIFACT_CAPABILITIES.get(resolved_capability)
        artifact = None
        if artifact_type and evaluation.decision == "accept":
            contract.artifact_contract = {"type": artifact_type, "required": True}
            artifact = build_artifact(name=self._artifact_name(prompt, artifact_type), artifact_type=artifact_type, content=self._artifact_content(answer, artifact_type), metadata={"capability": resolved_capability, "requested_capability": requested_capability, "capability_resolution": resolution_reason, "evaluation": evaluation.as_dict(), "cognitive_decision": decision, "task_contract": contract.to_dict(), "evidence_present": bool(evidence), "owner": "bitey_ia"})

        final_status = "completed" if evaluation.decision == "accept" else "needs_review"
        contract.transition(final_status, reason=None if final_status == "completed" else "evaluation_requires_review")
        return {"status": final_status, "answer": answer, "cognitive_decision": decision, "task_contract": contract.to_dict(), "requested_capability": requested_capability, "resolved_capability": resolved_capability, "research": research_result, "evaluation": evaluation.as_dict(), "artifact": artifact}

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
