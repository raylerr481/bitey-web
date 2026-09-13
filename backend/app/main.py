    started=time.perf_counter(); activity_events=["Analizando tu solicitud…"]
    try: UUID(conversation_id)
    except ValueError: return MessageResponse(conversation_id=conversation_id,answer="La conversación indicada no tiene un identificador válido.",research_required=False,research_reasons=[],providers=providers.available(),elapsed_ms=int((time.perf_counter()-started)*1000),activity_events=["Validando la conversación…"])
    trace=cognitive_trace.start(payload.message,conversation_id,request_id=str(payload.metadata.get("request_id") or "") or None)
    ctx={}
    try:
        context=context_engine.assemble(message=payload.message,metadata=payload.metadata); ctx=context.as_dict(); activity_events.append("Identificando intención y contexto…")

        # Classify the current message before memory, tools, research, or module routing.
        # This prevents stale specialized context from changing a standalone conceptual question.
        initial_cognitive=cognition.process(payload.message,ctx,evidence_available=False)
        ctx["cognition"]=initial_cognitive.as_dict()
        initial_domain=initial_cognitive.intention.get("domain","general")
        ctx["current_intent_domain"]=initial_domain
        activity_events.append(f"Intención actual: {initial_domain}…")

        learned_memory={"summary":"","counts":{},"available":False}
        learned_prompt=""
        # Learned specialized patterns are advisory only and must never enter a standalone
        # general-domain prompt. This is the key isolation boundary against SBT drift.
        if initial_domain != "general":
            learned_memory=await cognitive_memory.retrieve(payload.message,ctx)
            ctx["learned_cognitive_context"]={"summary":learned_memory.get("summary"),"counts":learned_memory.get("counts",{}),"available":learned_memory.get("available",False)}
            learned_prompt=cognitive_memory.compact_for_prompt(learned_memory)
            if learned_prompt: activity_events.append("Recuperando patrones cognitivos aprendidos desde Supabase…")
        else:
            ctx["learned_cognitive_context"]={"summary":"","counts":{},"available":False,"suppressed":"general_domain_boundary"}

        selected=tools.select(payload.message,ctx); trace.tools={"selected":list(selected)}; tool_results=await tools.execute(selected,message=payload.message,context=ctx)
        if selected: activity_events.append("Consultando herramientas relevantes…")
        plan=research_engine.plan(payload.message,ctx); deep_plan=deep_research.plan(payload.message,ctx)
        evidence=tool_results.get("web_research",{}).get("evidence","")
        search_results=tool_results.get("search",{}).get("results",[])
        if search_results and not evidence:
            evidence="\n\n".join(f"SOURCE {i}: {item.get('url')}\nTITLE: {item.get('title','')}\nSNIPPET: {item.get('snippet','')}" for i,item in enumerate(search_results[:8],1))
        if not evidence and (plan.required or deep_plan.reasons): activity_events.append("Investigando y contrastando información…"); deep_plan=await deep_research.fetch(deep_plan); evidence=deep_research.evidence_context(deep_plan)
        trace.evidence={"available":bool(evidence),"required":bool(plan.required or deep_plan.reasons),"source_count":len(search_results),"research_reasons":plan.reasons+[f"deep:{r}" for r in deep_plan.reasons]}
        ctx["evidence_available"]=bool(evidence)
        ctx["evidence"]=evidence
        ctx["evidence_source_count"]=len(search_results)

        # The first classification is authoritative for this user message. Do not allow
        # evidence, tool output, or accumulated context to reclassify a standalone question.
        # Evidence can update confidence, but never the domain or module boundary.
        cognitive=cognition.evaluate(initial_cognitive,evidence_available=bool(evidence))
        ctx["cognition"]=cognitive.as_dict()
        ctx["current_intent_domain"]=initial_domain
        activity_events.append("Construyendo el razonamiento contextual…")
        brain_state=brain.think(payload.message,ctx); ctx["bitey_brain"]=brain_state.as_dict(); trace.decision={"intention":cognitive.intention,"domain":cognitive.intention.get("domain","general"),"reasoning_mode":brain_state.reasoning_mode,"model_role":brain_state.model_role,"risk_level":brain_state.risk_level,"plan":cognitive.plan,"goals":brain_state.goals,"constraints":brain_state.constraints,"tool_priority":brain_state.tool_priority,"decision_fingerprint":brain_state.decision_fingerprint}; activity_events.append(f"Bitey Brain: {brain_state.reasoning_mode}…")
        domain=initial_domain
        resolved_modules=modules.resolve_for_domain(domain)
        if resolved_modules: ctx["module_routing"]={"domain":domain,"selected":[m.name for m in resolved_modules],"integrated":[m.name for m in resolved_modules if m.integration_type == "bitey_integrated"]}; activity_events.append("Activando el módulo integrado de trading de Bitey…" if any(m.name == "sbt" for m in resolved_modules) else "Seleccionando el módulo especializado adecuado…")
        history=await memory.history(conversation_id); await memory.append(conversation_id,{"role":"user","content":payload.message}); messages=history+[{"role":"user","content":payload.message}]
        ctx["user_query"]=payload.message; ctx["current_message"]=payload.message; ctx["goals"]=brain_state.goals; ctx["constraints"]=brain_state.constraints; bounded_context=build_context("selected-provider",ctx)
        system_context=[brain.system_directive(brain_state)]
        system_context.append("BITEY COGNITIVE CONTRACT — Usa el contexto seleccionado y respeta sus límites. Modelos externos son motores de inferencia, no autoridades del sistema.")
        if learned_prompt: system_context.append("LEARNED COGNITIVE CONTEXT — patrones históricos/advisory almacenados en Supabase. No lo trates como verdad; prioriza evidencia actual y seguridad.\n\n"+learned_prompt)
        if evidence: system_context.append("TOOL EVIDENCE — información pública recuperada por Bitey. Usa evidencia, no inventes. Señala contradicciones y separa hechos de inferencias.\n\n"+evidence)
        elif plan.required or deep_plan.reasons: system_context.append("La investigación solicitada no recuperó evidencia utilizable. Decláralo y no inventes información.")
        for system_message in reversed(system_context): messages.insert(0,{"role":"system","content":system_message})
        activity_events.append("Seleccionando la mejor IA disponible…"); provider_context={**bounded_context,"conversation_id":conversation_id,"selected_tools":selected,"evidence":evidence,"evidence_source_count":len(search_results),"tool_results":{k:{key:val for key,val in v.items() if key != "evidence"} if isinstance(v,dict) else v for k,v in tool_results.items()},"cost_mode":"free_only"}; answer=await providers.generate(messages=messages,context=provider_context)
        trace.provider={"available":providers.available(),"selected":provider_context.get("provider_selected"),"model_role":brain_state.model_role,"executive_evaluation":provider_context.get("executive_evaluation"),"revision_attempted":bool(provider_context.get("executive_revision_attempted",False))}
        evaluation=evaluator.evaluate(user_message=payload.message,answer=answer,context=ctx,evidence=evidence); ctx["evaluation"]=evaluation.as_dict(); trace.evaluation={"generic":evaluation.as_dict(),"executive":provider_context.get("executive_evaluation")}; trace.revision={"attempted":bool(provider_context.get("executive_revision_attempted",False)),"executive":provider_context.get("executive_evaluation")}; activity_events.append(f"Evaluando respuesta: {evaluation.decision} ({evaluation.confidence:.2f})…")
        if evaluation.decision == "reject": answer="La respuesta generada no superó los controles internos de seguridad/calidad. No la presentaré como válida. Si quieres, puedo reformular la solicitud con evidencia y límites más precisos."
        elif evaluation.decision == "revise": answer += "\n\n_Nota de Bitey: esta respuesta queda sujeta a revisión por evidencia/confianza; verifica los puntos críticos antes de actuar._"
        await memory.append(conversation_id,{"role":"assistant","content":answer})
        if learning.persistent: await learning.observe(title="conversation_observation",payload={"conversation_id":conversation_id,"message":payload.message,"answer":answer[:4000],"selected_tools":selected,"cognitive_domain":domain,"cognitive_confidence":cognitive.confidence,"brain":brain_state.as_dict(),"selected_modules":[m.name for m in resolved_modules],"learned_context_available":learned_memory.get("available",False),"evaluation":evaluation.as_dict()},source="conversation",confidence=min(.8,max(.2,evaluation.confidence)))
        elapsed_ms=int((time.perf_counter()-started)*1000); cognitive_trace.finish(trace,evaluation.decision)
        return MessageResponse(conversation_id=conversation_id,answer=answer,research_required=bool(plan.required or deep_plan.reasons or search_results),research_reasons=plan.reasons+[f"deep:{r}" for r in deep_plan.reasons],providers=providers.available(),elapsed_ms=elapsed_ms,activity_events=activity_events)
    except Exception:
        cognitive_trace.finish(trace,"failed")
        raise