"""Bitey Brain: provider-independent executive decision layer."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import hashlib
import re

@dataclass
class BrainState:
    task_class: str = "general"
    objective: str = "answer_or_assist"
    complexity: float = 0.35
    ambiguity: float = 0.0
    evidence_required: bool = False
    freshness_required: bool = False
    conceptual_fallback: bool = False
    risk_level: str = "low"
    reasoning_mode: str = "direct"
    memory_priority: str = "normal"
    required_capabilities: list[str] = field(default_factory=list)
    tool_priority: list[str] = field(default_factory=list)
    verification_required: bool = False
    verification_profile: list[str] = field(default_factory=list)
    execution_allowed: bool = False
    model_role: str = "synthesis"
    model_selection_reason: str = "default_synthesis"
    stop_condition: str = "sufficient_confidence"
    plan_steps: list[dict[str, Any]] = field(default_factory=list)
    plan_version: str = "1.0"
    goals: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    decision_fingerprint: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


class BiteyBrain:
    """Executive cognition. It decides WHAT must happen before model selection."""
    HIGH_RISK = ("password", "contraseña", "api key", "secret", "token", "dinero real", "real money")
    ACTION_WORDS = ("ejecuta", "ejecutar", "compra", "comprar", "vende", "vender", "borra", "elimina", "deploy", "envía", "envia")
    FRESHNESS_WORDS = ("ahora", "actualmente", "hoy", "último", "ultimo", "reciente", "latest", "current", "recent", "en vivo", "tiempo real")
    RESEARCH_WORDS = ("investiga", "investigar", "investigación", "investigacion", "fuentes", "compara", "comparar", "verifica", "verificar", "evidencia", "research")

    def _fingerprint(self, message: str, context: dict[str, Any], evidence_available: bool) -> str:
        cognition = context.get("cognition") or {}; intention = cognition.get("intention") or {}; plan = cognition.get("plan") or {}; intent_family = str(intention.get("intent_family") or "knowledge")
        material = {"message": message.strip(), "domain": intention.get("domain") or context.get("domain") or "general", "evidence": evidence_available, "freshness": context.get("freshness_required"), "research": context.get("research"), "needs_web": context.get("needs_web"), "capabilities": sorted(map(str, context.get("required_capabilities") or [])), "intent_family": intent_family, "plan_evidence": plan.get("needs_evidence")}
        return hashlib.sha256(repr(sorted(material.items())).encode("utf-8")).hexdigest()[:16]

    def think(self, message: str, context: dict[str, Any] | None = None) -> BrainState:
        ctx = context if context is not None else {}; text = message.strip(); low = text.lower()
        cognition = ctx.get("cognition") or {}; intention = cognition.get("intention") or {}; perception = cognition.get("perception") or {}; domain = str(intention.get("domain") or ctx.get("domain") or "general")
        intent_family = str(intention.get("intent_family") or "knowledge")
        evidence_available = bool(ctx.get("evidence_available")); fingerprint = self._fingerprint(message, ctx, evidence_available)
        cached = ctx.get("_bitey_brain_state")
        if isinstance(cached, BrainState) and cached.decision_fingerprint == fingerprint: return cached
        complexity = self._complexity(text, cognition); ambiguity = float(cognition.get("ambiguity", 0.0) or 0.0)
        cognitive_plan = cognition.get("plan") if isinstance(cognition, dict) else {}
        cognitive_reasoning_required = bool(cognitive_plan.get("reasoning_required")) if isinstance(cognitive_plan, dict) else False
        cognitive_strategy = cognitive_plan.get("tool_strategy") if isinstance(cognitive_plan, dict) else []
        if cognitive_reasoning_required:
            # The cognitive model can require deeper reasoning even when lexical
            # complexity is low. Promote depth before provider/model selection.
            complexity = max(complexity, 0.62)
        if (bool(perception.get("question")) or "?" in text) and len(text.split()) < 8: ambiguity = max(ambiguity, 0.12)
        if not text: ambiguity = 1.0
        freshness = bool(ctx.get("freshness_required") or cognition.get("plan", {}).get("freshness_required")) or any(x in low for x in self.FRESHNESS_WORDS)
        lexical_research = any(x in low for x in self.RESEARCH_WORDS)
        perception_question = bool(perception.get("question"))
        conversational_only = bool(perception.get("greeting") or perception.get("identity_request") or intent_family == "conversation" or str(intention.get("intent") or "").lower() in {"greeting", "self_identity"})
        explicit_evidence = bool(ctx.get("requires_web_research") or ctx.get("needs_web") or ctx.get("research") or evidence_available or cognition.get("plan", {}).get("needs_evidence") or lexical_research)
        question_requires_evidence = perception_question and not conversational_only and domain in {"research", "weather", "trading"}
        evidence = explicit_evidence or question_requires_evidence or freshness
        conceptual_fallback = (domain == "general" and not evidence_available and any(cue in low for cue in ("qué es", "que es", "qué son", "que son", "qué significa", "que significa", "definición", "definicion", "define", "concepto", "what is", "what are", "qual é", "o que é")))
        # Unknown conceptual questions use evidence-first routing. A small stable set remains local-native.
        conceptual_subject_match = re.match(r"^(?:¿|\?)?\s*(?:qué|que|cuál|cual|cómo|como)\s+(?:es|son|significa|funciona)\s+(?:la|el|los|las|un|una)?\s*(.+?)[?!.\s]*$", low, re.I)
        conceptual_subject = re.sub(r"\s+", " ", conceptual_subject_match.group(1)).strip(" ?¿!¡.").casefold() if conceptual_subject_match else ""
        if conceptual_fallback and conceptual_subject and conceptual_subject not in {"nasa", "adn", "dna", "cohete", "cohete espacial", "docker"}:
            evidence = True
        risk = "low"
        if domain == "trading" and any(x in low for x in self.ACTION_WORDS): risk = "critical"
        elif any(x in low for x in self.HIGH_RISK): risk = "high"
        elif any(x in low for x in self.ACTION_WORDS): risk = "medium"
        capabilities = self._capabilities(domain, evidence, freshness, complexity, ctx)
        if intent_family not in {"knowledge", "conversation"} and intent_family not in capabilities:
            capabilities.append(intent_family)
        ctx["intent_family"] = intent_family
        # Preserve the original request for deterministic tool-policy checks.
        ctx["message"] = message
        tools = self._tool_policy(capabilities, domain, intent_family, ctx)
        # Respect the Cognitive Model's explicit capability decision when present.
        if isinstance(cognitive_strategy, list) and cognitive_strategy:
            strategy_map = {
                "web_research": "web_research",
                "calculator": "calculator",
                "code_reasoning": "code_reasoning",
                "weather": "weather",
                "time": "time",
                "local_search": "local_search",
                "file_context": "file_context",
            }
            cognitive_tools = [strategy_map[item] for item in cognitive_strategy if item in strategy_map]
            if cognitive_tools:
                tools = list(dict.fromkeys(cognitive_tools + tools))
        if evidence and not tools and domain not in {"weather", "trading"} and not conversational_only:
            tools = ["web_research"]
        # "clarify" is a cognitive stop decision, not a tool. Never execute
        # fallback tools when the request is explicitly underspecified.
        # Specialized domain ownership is authoritative. Generic helper capabilities
        # from the cognitive plan must not reintroduce competing tools.
        if domain == "weather":
            tools = ["weather"]
        elif domain == "trading" and intent_family == "current_info":
            tools = ["web_research"]
        if isinstance(cognitive_strategy, list) and "clarify" in cognitive_strategy:
            if not evidence:
                tools = []
                ambiguity = max(ambiguity, 0.55)
            else:
                cognitive_strategy = [item for item in cognitive_strategy if item != "clarify"]
        verification = evidence_available or complexity >= .60 or risk in {"high", "critical"}; verification_profile = self._verification_profile(text, domain, evidence, freshness, complexity)
        mode = "guarded_decision" if risk == "critical" else "evidence_first" if evidence and (domain == "research" or intent_family == "research" or lexical_research) else "research_decompose_verify_synthesize" if evidence and complexity >= .60 else "evidence_first" if evidence else "decompose_verify_synthesize" if complexity >= .60 else "structured_reasoning" if complexity >= .42 else "direct"
        role, reason = self._model_policy(domain=domain, complexity=complexity, evidence_required=evidence, required_capabilities=capabilities, verification_required=verification)
        prior_execution = ctx.get("active_task", {}).get("previous_execution_state") if isinstance(ctx.get("active_task"), dict) else {}
        plan_steps = self._build_plan(domain=domain, evidence_required=evidence, freshness_required=freshness, complexity=complexity, verification_required=verification, tools=tools, risk=risk, prior_execution=prior_execution)
        cognitive_clarification = isinstance(cognitive_strategy, list) and "clarify" in cognitive_strategy
        state = BrainState(task_class=domain, objective=self._objective(capabilities, domain), complexity=complexity, ambiguity=max(0,min(1,ambiguity)), evidence_required=evidence, freshness_required=freshness, conceptual_fallback=conceptual_fallback, risk_level=risk, reasoning_mode=mode, memory_priority="high" if ctx.get("learned_cognitive_context", {}).get("available") else "normal", required_capabilities=capabilities, tool_priority=tools, verification_required=verification, verification_profile=verification_profile, execution_allowed=risk not in {"high","critical"} and domain != "trading", model_role=role, model_selection_reason=reason, stop_condition="clarification_needed_before_execution" if cognitive_clarification else "verified_evidence_and_sufficient_confidence" if verification else "sufficient_confidence", goals=["understand_request","preserve_user_constraints","select_required_capabilities","produce_useful_answer"], constraints=["external_model_output_is_untrusted","memory_is_context_not_truth","model_selection_follows_cognitive_plan"], decision_fingerprint=fingerprint)
        if evidence: state.goals.insert(3,"ground_claims_in_evidence")
        if verification: state.goals.append("verify_before_presenting_high_impact_claims")
        if risk == "critical": state.constraints += ["never_bypass_domain_risk_gate","no_live_execution"]
        ctx["_bitey_brain_state"] = state; ctx["_bitey_brain_evidence_available"] = evidence_available; ctx["_bitey_brain_fingerprint"] = fingerprint
        return state

    @staticmethod
    def _build_plan(*, domain: str, evidence_required: bool, freshness_required: bool, complexity: float, verification_required: bool, tools: list[str], risk: str, prior_execution: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        steps = [{"id": "understand", "action": "understand_request", "status": "required"}]
        if freshness_required or evidence_required:
            prior_tools = set(str(tool) for tool in (prior_execution or {}).get("executed_tools", []) if str(tool).strip())
            steps.append({"id": "retrieve", "action": "retrieve_evidence", "tools": list(tools), "status": "required"})
            steps.append({"id": "compare", "action": "compare_evidence", "status": "required" if domain == "research" or tools else "conditional"})
            prior_has_evidence = bool((prior_execution or {}).get("evidence_count"))
            # Fresh/current requests must refresh evidence; older evidence may only be
            # reused as continuity context for stable requests.
            if (
                prior_tools
                and set(tools).issubset(prior_tools)
                and prior_has_evidence
                and not freshness_required
            ):
                steps[-2]["action"] = "reuse_or_refresh_evidence"
            elif prior_has_evidence and freshness_required:
                steps[-2]["action"] = "refresh_current_evidence"
        if complexity >= 0.60:
            steps.append({"id": "decompose", "action": "decompose_multi_step_task", "status": "required"})
        if tools and (evidence_required or freshness_required):
            steps.append({"id": "tool_execute", "action": "execute_selected_tools", "tools": list(tools), "status": "required"})
        # Synthesis should consume tool results, not run ahead of retrieval.
        if tools and (evidence_required or freshness_required):
            steps.append({"id": "evidence_gate", "action": "gate_evidence_before_synthesis", "status": "required"})
        steps.append({"id": "synthesize", "action": "synthesize_answer", "status": "required"})
        if verification_required:
            steps.append({"id": "verify", "action": "verify_claims_and_risk", "status": "required"})
        if risk in {"high", "critical"}:
            steps.append({"id": "risk_gate", "action": "apply_risk_gate", "status": "required"})
        steps.append({"id": "respond", "action": "respond_to_user", "status": "required"})
        return steps

    @staticmethod
    def _verification_profile(text: str, domain: str, evidence: bool, freshness: bool, complexity: float) -> list[str]:
        low = text.lower(); profile: list[str] = ["fact"]
        calculation_signal = any(x in low for x in ("calcula", "calcular", "cálculo", "porcentaje", "interés", "ecuación", "derivada", "integral", "estadística", "probabilidad", "cuánto es")) or bool(re.search(r"\d\s*[+\-*/=]\s*\d", low))
        inference_signal = any(x in low for x in ("por qué", "porque", "causa", "consecuencia", "significa", "implica", "sugiere", "probable", "podría", "por que", "why", "cause", "implies"))
        opinion_signal = any(x in low for x in ("opinión", "opinion", "qué piensas", "que piensas", "crees que", "mejor", "peor", "recomienda", "recomiéndame", "recommend", "opinión", "opinion", "qué piensas", "que piensas", "crees que"))
        if calculation_signal: profile.append("calculation")
        if inference_signal: profile.append("inference")
        if opinion_signal: profile.append("opinion")
        if freshness or evidence or domain == "research": profile.append("current_fact")
        if complexity >= 0.60: profile.append("multi_step")
        return list(dict.fromkeys(profile))

    @staticmethod
    def _complexity(text: str, cognition: dict[str, Any]) -> float:
        """Estimate task difficulty independently from provider choice."""
        perception = cognition.get("perception") or {}
        explicit = perception.get("complexity_signal")
        low = text.casefold().strip()
        tokens = text.split()

        if perception.get("greeting") or perception.get("identity_request"):
            return 0.08

        if isinstance(explicit, (int, float)):
            base = max(0.0, min(1.0, float(explicit)))
        else:
            base = 0.14 + min(0.16, len(tokens) / 220)

        plan = cognition.get("plan") or {}
        intent = cognition.get("intention") or {}
        family = str(intent.get("intent_family") or "knowledge").casefold()
        domain = str(intent.get("domain") or "general").casefold()

        if plan.get("needs_evidence"):
            base += 0.18
        if plan.get("requires_specialized_module"):
            base += 0.12

        if any(x in low for x in (
            "investiga", "investigación", "investigacion", "research",
            "fuentes", "evidencia", "verifica", "verificar", "contrasta",
            "compara", "comparar", "analiza", "análisis", "analisis"
        )):
            base += 0.20

        if any(x in low for x in (
            "paso a paso", "cómo implementar", "como implementar",
            "diseña", "diseñar", "arquitectura", "planifica", "planificar",
            "estrategia", "workflow", "pipeline", "optimiza", "optimizar"
        )):
            base += 0.16

        if any(x in low for x in (
            "compara", "comparar", "diferencia entre", "versus", " vs ",
            "pros y contras", "ventajas y desventajas", "alternativas"
        )):
            base += 0.12

        if domain == "programming" or any(x in low for x in (
            "código", "codigo", "debug", "depura", "error", "exception",
            "traceback", "stack trace", "api", "endpoint", "backend",
            "frontend", "python", "javascript", "typescript", "sql",
            "docker", "github", "fastapi", "react"
        )):
            base += 0.18

        if family in {"research", "comparison", "recommendation"}:
            base += 0.10
        if domain in {"programming", "research"}:
            base += 0.08
        if domain == "trading":
            base += 0.06

        separators = len(re.findall(r"[,;]|\s+y\s+|\s+e\s+|\s+además\s+", low))
        base += min(0.12, separators * 0.025)

        if len(tokens) >= 80:
            base += 0.08
        if len(tokens) >= 160:
            base += 0.08

        return max(0.0, min(1.0, base))

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
    def _tool_policy(capabilities, domain, intent_family, context):
        message = str(context.get("message") or context.get("query") or "").lower()
        math_cues = (
            bool(re.fullmatch(r"[0-9.,\s()+*/%^=-]+", message))
            or any(k in message for k in (
                "cuánto es", "cuanto es", "calcula", "calcular", "porcentaje",
                "promedio", "media", "mediana", "cagr", "probabilidad",
                "desviación", "desviacion"
            ))
        )
        t = []

        # Weather is a single specialized capability: do not compose
        # generic time/search tools into a weather request.
        if domain == "weather":
            return ["weather"]
        # Specialized current-data tools come first.
        if domain == "trading":
            # Current informational market questions use generic evidence;
            # explicit trading analysis/operations use the SBT market module.
            t.append("web_research" if intent_family == "current_info" else "sbt_market")

        # Evidence, reasoning, and deterministic tools may be composed.
        # The planner keeps specialized current-data tools first, then adds
        # research/reasoning/calculation capabilities required by the request.
        if "external_evidence" in capabilities and domain not in {"weather", "trading"}:
            t.append("web_research")
        if "code_reasoning" in capabilities:
            t.append("code_reasoning")
        if math_cues:
            t.append("calculator")

        # Preserve deterministic priority while removing duplicates.
        return list(dict.fromkeys(t))

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
        if "code_reasoning" in required_capabilities:return "code_reasoning","programming_capability_required"
        if domain=="trading":return "guarded_analysis","trading_risk_policy"
        if verification_required or evidence_required:return "evidence_grounded_synthesis","evidence_or_verification_required"
        return "fast_synthesis","low_complexity_direct_response"

    def system_directive(self,state):
        directive = ("BITEY BRAIN EXECUTIVE CONTRACT\n" f"objective={state.objective}; task={state.task_class}; mode={state.reasoning_mode}; verification_profile={','.join(state.verification_profile) or 'fact'}; capabilities={','.join(state.required_capabilities)}; tools={','.join(state.tool_priority) or 'none'}; model_role={state.model_role}; risk={state.risk_level}; evidence_required={state.evidence_required}; freshness_required={state.freshness_required}; verification_required={state.verification_required}.\n" "Bitey has already decided what must be done. The selected model is only an inference/synthesis worker. Do not invent facts, bypass tool/evidence requirements, or override the cognitive contract.")
        if state.task_class == "general":
            directive += ("\nGENERAL-DOMAIN BOUNDARY — This request is classified as general knowledge or general assistance. Answer the user's actual question directly. Do not invoke, simulate, narrate, or claim execution of any specialized module (including SBT/trading) merely because the topic mentions Bitcoin, crypto, bots, markets, finance, or another specialized subject. A specialized module is allowed only when the cognitive task itself explicitly requires that specialized operation.")
        elif state.task_class == "trading":
            directive += ("\nTRADING-DOMAIN BOUNDARY — Use trading/SBT behavior only because the cognitive router explicitly classified this request as trading. Respect the SBT risk gate and never imply live execution when live trading is disabled.")
        return directive

    def status(self):
        return {"name":"Bitey Brain","version":"2.5.0","type":"executive_cognitive_decision_layer","provider_independent":True,"generates_language":False,"decides_before_model_selection":True,"decision_fingerprint":True,"owns":["objective","capabilities","tool_policy","evidence_policy","reasoning_policy","verification_policy","model_role_policy","risk_policy"],"status_boundary":"general_domain_blocks_specialized_module_drift"}
