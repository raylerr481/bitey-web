/**
 * Bitey Cognitive Tool Orchestrator
 *
 * Keeps tool selection separate from model generation. The orchestrator:
 * 1. understands intent/domain metadata,
 * 2. decides whether external evidence is actually needed,
 * 3. builds an ordered tool plan,
 * 4. records fallback tools,
 * 5. never claims a tool ran unless the worker reports execution.
 *
 * All tools are free-only and side-effect free at the planning layer.
 */

const TOOL_DEFINITIONS = {
  time: { id:'time', kind:'specialized_data', domains:['time'], intents:['time','current_information'], priority:105, fallbacks:['web_search'] },
  weather: { id:'weather', kind:'specialized_data', domains:['weather'], intents:['weather','current_information'], priority:100, fallbacks:['web_search'] },
  web_search: { id:'web_search', kind:'research', domains:['research','finance','jobs','business','code','general'], intents:['research','current_information','comparison','question'], priority:80, fallbacks:[] },
  calculator: { id:'calculator', kind:'deterministic', domains:['math','finance','analysis','general'], intents:['calculation','question'], priority:110, fallbacks:['model_reasoning'] },
  code_reasoning: { id:'code_reasoning', kind:'reasoning', domains:['code'], intents:['code','question'], priority:90, fallbacks:['model_reasoning'] },
  model_reasoning: { id:'model_reasoning', kind:'generation', domains:['general'], intents:['conversation','question','comparison','research','current_information','code'], priority:10, fallbacks:[] }
};

const GREETING_RE = /^(hola|hi|hello|olá|oi|buenas?)(?:[!,.\s].*)?$/i;
const EXPLICIT_RESEARCH_RE = /\b(busca|buscar|búsqueda|investiga|investigar|investigación|fuentes|contrasta|search|research)\b/i;
const FRESHNESS_RE = /\b(hoy|ahora|actual(?:mente)?|actualizado|últim[oa]s?|latest|news|noticias?|precio(?:s)?|cotización|cotiza|cuánto cuesta|recent|recently|recentemente)\b/i;
const CURRENT_ENTITY_RE = /\b(qué|que|quién|quien|where|who|when|cuál|cual)\b/i;
const CONCEPTUAL_RE = /^\s*(?:qué es|que es|qué significa|que significa|define|definición|definicion|cómo funciona|como funciona|explica|explícame|explicame|what is|how does)\b/i;
const DEEP_RE = /\b(paso a paso|analiza|analizar|análisis|analisis|planifica|planificar|diseña|diseñar|arquitectura|profundo|profundamente|detalladamente|deep|complex|audita|auditar|revisa|revisar)\b/i;
const MULTI_TASK_RE = /\b(y además|y tambien|y también|además|también|tambien|then|also|and)\b/i;

export function evaluateIntent({ language = {}, route = {}, message = '', context = {} } = {}) {
  const text = String(message || '').trim();
  const lower = text.toLowerCase();
  const domains = new Set((language.domains || []).map(item => item?.domain).filter(Boolean));
  const explicitMode = String(route?.mode || context?.mode || 'auto').toLowerCase();
  const normalizedIntent = String(language.intent || route.intent || 'question').toLowerCase();
  const conceptual = CONCEPTUAL_RE.test(lower);
  const greeting = GREETING_RE.test(lower);

  const signals = {
    current: FRESHNESS_RE.test(lower),
    time: normalizedIntent === 'time' || domains.has('time') || /\b(hora|horario|time)\b/i.test(lower) || /\bqu[eé]\s+tiempo\s+es\b/i.test(lower),
    weather: domains.has('weather') || normalizedIntent === 'weather' || /\b(clima|weather|forecast|previs[aã]o|temperatura)\b/i.test(lower),
    research: EXPLICIT_RESEARCH_RE.test(lower),
    calculation: /(?:cuánto es|cu[aá]nto|calcula|calcular|calculate|compute|porcentaje|roi|\b\d+(?:[.,]\d+)?\s*[+*\/\-]\s*\d)/i.test(lower) || normalizedIntent === 'calculation' || domains.has('math'),
    code: normalizedIntent === 'code' || domains.has('code') || /\b(código|code|python|javascript|typescript|sql|api|bug|error|github|stack trace)\b/i.test(lower),
    comparison: normalizedIntent === 'comparison' || /\b(compara|comparar|comparativa|comparativas|versus|\bvs\.?\b|diferencia|alternativas|opciones)\b/i.test(lower),
    context_followup: Array.isArray(context?.references) && context.references.length > 0,
    long_or_complex: text.length > 240 || DEEP_RE.test(lower),
    multi_task: MULTI_TASK_RE.test(lower) && text.length > 80
  };

  // "where/who/when" alone are not freshness signals. They need an entity/current
  // context to justify external evidence. This prevents conceptual questions from
  // falling into generic web search.
  signals.entity_lookup = CURRENT_ENTITY_RE.test(lower) && !conceptual;
  signals.fresh_entity_lookup = signals.entity_lookup && (
    signals.current || /\b(ahora|actual|actualmente|latest|today|recent)\b/i.test(lower)
  );

  let primaryIntent = normalizedIntent;
  if (greeting) primaryIntent = 'conversation';
  else if (signals.time) primaryIntent = 'time';
  else if (signals.weather) primaryIntent = 'weather';
  else if (signals.calculation) primaryIntent = 'calculation';
  else if (signals.code) primaryIntent = 'code';
  else if (signals.comparison) primaryIntent = 'comparison';
  else if (signals.research) primaryIntent = 'research';
  else if (signals.current || signals.fresh_entity_lookup) primaryIntent = 'current_information';
  else if (signals.entity_lookup) primaryIntent = 'question';
  else if (normalizedIntent === 'conversation') primaryIntent = 'conversation';

  const explicitResearchMode = explicitMode === 'investigación' || explicitMode === 'research';
  const explicitMathMode = explicitMode === 'matemática' || explicitMode === 'math';
  const explicitCodeMode = explicitMode === 'código' || explicitMode === 'code';
  // Named-entity questions usually need external grounding, while conceptual
  // definitions remain direct unless the user explicitly asks for research.
  const entityEvidenceRequired = signals.entity_lookup && !conceptual;
  const externalEvidenceRequired = explicitResearchMode
    || signals.research
    || signals.current
    || signals.fresh_entity_lookup
    || entityEvidenceRequired
    || signals.comparison && !conceptual
    || signals.weather
    || signals.time
    || Boolean(route?.research_required);

  let complexity = 'simple';
  if (signals.long_or_complex || signals.context_followup || signals.multi_task) complexity = 'complex';
  else if (externalEvidenceRequired || signals.calculation || signals.code || signals.comparison) complexity = 'moderate';

  let reasoningLevel = complexity === 'complex' ? 'deep' : complexity === 'moderate' ? 'standard' : 'fast';
  if (signals.context_followup && reasoningLevel === 'fast') reasoningLevel = 'standard';
  if (explicitResearchMode && reasoningLevel === 'fast') reasoningLevel = 'standard';

  let toolNeed = 'none';
  if (explicitMathMode || signals.calculation) toolNeed = 'calculator';
  else if (signals.time) toolNeed = 'time';
  else if (signals.weather) toolNeed = 'weather';
  else if (explicitCodeMode || signals.code) toolNeed = 'code_reasoning';
  else if (externalEvidenceRequired) toolNeed = 'web_search';

  // Explicit UI modes are hard overrides, while Auto remains evidence-driven.
  if (explicitMathMode) toolNeed = 'calculator';
  if (explicitCodeMode) toolNeed = 'code_reasoning';
  if (explicitResearchMode) toolNeed = 'web_search';

  const activeSignals = Object.values(signals).filter(Boolean).length;
  const ambiguity = (signals.current && signals.entity_lookup && !signals.fresh_entity_lookup) ? 0.06 : (activeSignals >= 4 ? 0.04 : 0);
  const confidence = Math.max(0.58, Math.min(0.99, 0.74 + activeSignals * 0.03 - ambiguity));

  const intentParts = [];
  if (externalEvidenceRequired) intentParts.push('external_evidence');
  if (signals.current) intentParts.push('current_information');
  if (signals.time) intentParts.push('time');
  if (signals.weather) intentParts.push('weather');
  if (entityEvidenceRequired) intentParts.push('external_evidence');
  if (signals.calculation) intentParts.push('calculation');
  if (signals.code) intentParts.push('code');
  if (signals.comparison) intentParts.push('comparison');
  if (signals.context_followup) intentParts.push('context_followup');
  if (signals.multi_task) intentParts.push('multi_task');
  if (!intentParts.length) intentParts.push(primaryIntent);

  const selectedIntentParts = [...new Set(intentParts)];
  return {
    intent: primaryIntent,
    intent_parts: selectedIntentParts,
    multi_intent: selectedIntentParts.length > 1,
    confidence,
    complexity,
    reasoning_level: reasoningLevel,
    tool_need: toolNeed,
    explicit_mode: explicitMode,
    signals,
    reasoning: {
      level: reasoningLevel,
      external_evidence: externalEvidenceRequired,
      tool_count_hint: toolNeed === 'none' ? 0 : 1,
      conceptual_direct_answer: conceptual && !externalEvidenceRequired,
      context_aware: signals.context_followup
    },
    should_research: toolNeed === 'web_search',
    should_use_specialized_tool: ['time','weather','calculator','code_reasoning'].includes(toolNeed),
    fallback_to_model: true
  };
}

export function selectTools({ language = {}, route = {}, message = '', context = {} } = {}) {
  const intentEval = evaluateIntent({ language, route, message, context });
  const domains = new Set((language.domains || []).map(item => item?.domain).filter(Boolean));
  const intent = String(intentEval.intent || language.intent || route.intent || 'question');
  const candidates = [];
  const parts = new Set(intentEval.intent_parts || [intent]);

  if (intent === 'time' || domains.has('time') || parts.has('time')) candidates.push('time');
  if (intent === 'weather' || domains.has('weather') || parts.has('weather')) candidates.push('weather');
  if (isCalculation(message, intent, domains) || parts.has('calculation')) candidates.push('calculator');
  if (intent === 'code' || domains.has('code') || parts.has('code')) candidates.push('code_reasoning');

  const researchRequired = Boolean(
    route.research_required ||
    intentEval.should_research ||
    intentEval.reasoning?.external_evidence ||
    parts.has('external_evidence')
  );
  if (researchRequired) candidates.push('web_search');

  candidates.push('model_reasoning');

  const unique = [...new Set(candidates)];
  const primary = unique[0] || 'model_reasoning';
  const chain = [];
  for (const id of unique) {
    if (!chain.includes(id)) chain.push(id);
    for (const fallback of TOOL_DEFINITIONS[id]?.fallbacks || []) {
      if (!chain.includes(fallback)) chain.push(fallback);
    }
  }

  const toolCountHint = unique.filter(id => id !== 'model_reasoning').length;
  const reasoning = {
    ...(intentEval.reasoning || {}),
    tool_count_hint: toolCountHint,
    selected_tools: unique
  };

  return {
    primary,
    ordered: chain,
    fallbacks: chain.slice(1),
    selected: unique,
    reason: buildReason(primary, intent, domains, intentEval),
    intent_evaluation: intentEval,
    reasoning,
    tool_registry_version: '1.1'
  };
}

export function buildToolActivity(plan) {
  const primary = TOOL_DEFINITIONS[plan?.primary];
  if (!primary) return 'Análisis directo seleccionado.';
  const labels = {
    time:'Consulta de hora actual iniciada mediante reloj determinista.',
    weather:'Consulta meteorológica verificada iniciada.',
    web_search:'Búsqueda web seleccionada para recopilar evidencia.',
    calculator:'Cálculo determinista seleccionado.',
    code_reasoning:'Análisis de código seleccionado.',
    model_reasoning:'Razonamiento directo seleccionado.'
  };
  return labels[primary.id] || 'Herramienta seleccionada según la intención.';
}

export function toolLabel(id) {
  return ({time:'hora actual',weather:'meteorología',web_search:'búsqueda web',calculator:'cálculo',code_reasoning:'análisis de código',model_reasoning:'razonamiento'})[id] || String(id || 'herramienta');
}

function isCalculation(message, intent, domains) {
  if (intent === 'calculation') return true;
  if (domains.has('math')) return true;
  return /(?:cu[aá]nto es|calcula|calcular|calculate|compute|suma|resta|multiplica|divide|porcentaje|%|\b\d+(?:[.,]\d+)?\s*[+*\/\-]\s*\d)/i.test(String(message || ''));
}

function buildReason(primary, intent, domains, intentEval = {}) {
  if (primary === 'time') return 'time_intent';
  if (primary === 'weather') return 'weather_intent';
  if (primary === 'calculator') return 'deterministic_calculation';
  if (primary === 'code_reasoning') return 'code_domain';
  if (primary === 'web_search') return intentEval?.reasoning?.external_evidence ? 'external_evidence_required' : 'research_or_current_information';
  return intent === 'conversation' ? 'conversation' : (intentEval?.reasoning?.conceptual_direct_answer ? 'conceptual_direct_reasoning' : 'direct_reasoning');
}

export function getToolRegistry() {
  return Object.values(TOOL_DEFINITIONS).map(tool => ({
    id:tool.id, kind:tool.kind, domains:tool.domains, intents:tool.intents, priority:tool.priority, fallbacks:tool.fallbacks
  }));
}

export function buildCompoundPlan({ language = {}, route = {}, message = '', context = {} } = {}) {
  const base = selectTools({ language, route, message, context });
  const text = String(message || '').toLowerCase();
  const evalSignals = base.intent_evaluation?.signals || {};
  const reasoning = base.intent_evaluation?.reasoning || {};
  const steps = [];
  const add = (tool, purpose) => {
    if (!steps.some(step => step.tool === tool)) steps.push({order:steps.length+1,tool,purpose});
  };

  if (base.primary === 'time') add('time','obtener la hora actual de la ubicación solicitada');
  if (base.primary === 'weather') add('weather','obtener datos meteorológicos actuales');
  if (base.selected.includes('web_search')) add('web_search','recopilar y contrastar evidencia externa');
  if (base.selected.includes('calculator')) add('calculator','realizar cálculos deterministas');
  if (base.selected.includes('code_reasoning')) add('code_reasoning','analizar código y resultados técnicos');

  // Adaptive compound planning: add a second tool only when the task contains
  // a real dependency between evidence and computation/reasoning.
  const comparisonTask = /\b(compara|comparar|comparativa|contrasta|versus|vs\.?)\b/i.test(text);
  const derivationTask = /\b(calcula|calcular|cu[aá]nto|cu[aá]ntas|porcentaje|roi|retorno|rentabilidad|inversi[oó]n|recuperar|recuperaci[oó]n|mensual|anual|por d[ií]a|coste|costo|precio)\b/i.test(text);
  const multiTask = Boolean(
    evalSignals.multi_task ||
    comparisonTask ||
    (reasoning.external_evidence && derivationTask && /\b(y|adem[aá]s|tamb[ié]n|para|con|cu[aá]nto)\b/i.test(text))
  );

  if (multiTask) {
    if (reasoning.external_evidence && !steps.some(step => step.tool === 'web_search')) {
      add('web_search','recopilar evidencia externa necesaria para los datos de entrada');
    }
    if (derivationTask && !steps.some(step => step.tool === 'calculator')) {
      add('calculator','calcular magnitudes derivadas a partir de los datos disponibles');
    }
    if ((comparisonTask || evalSignals.comparison) && !steps.some(step => step.tool === 'web_search') && reasoning.external_evidence) {
      add('web_search','contrastar las alternativas antes de sintetizar');
    }
  }

  if (!steps.length) add('model_reasoning','sintetizar la respuesta con razonamiento directo');

  const dependencyOrder = ['time','weather','web_search','calculator','code_reasoning','model_reasoning'];
  const orderedSteps = steps
    .slice()
    .sort((a,b)=>dependencyOrder.indexOf(a.tool)-dependencyOrder.indexOf(b.tool))
    .map((step,index)=>({...step,order:index+1}));

  const dependencies = orderedSteps.map(step => {
    const dependsOn = [];
    if (step.tool === 'calculator' && orderedSteps.some(item=>item.tool==='web_search')) dependsOn.push('web_search');
    if (step.tool === 'model_reasoning' && orderedSteps.length > 1) {
      dependsOn.push(...orderedSteps.filter(item=>item.tool!=='model_reasoning').map(item=>item.tool));
    }
    return {step:step.order,tool:step.tool,depends_on:[...new Set(dependsOn)]};
  });

  return {
    ...base,
    primary: orderedSteps[0]?.tool || base.primary,
    compound: orderedSteps.length > 1,
    steps: orderedSteps,
    dependencies,
    reasoning: {
      ...(base.reasoning || {}),
      tool_count_hint: orderedSteps.filter(step => step.tool !== 'model_reasoning').length,
      compound_reason: orderedSteps.length > 1
        ? (steps.some(step => step.tool === 'calculator') && steps.some(step => step.tool === 'web_search')
          ? 'evidence_then_deterministic_calculation'
          : 'multi_tool_dependency')
        : 'single_tool_or_direct_reasoning'
    },
    execution_policy:'execute_in_order_and_report_actual_results'
  };
}
