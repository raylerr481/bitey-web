/**
 * Bitey Cognitive Tool Orchestrator
 *
 * Keeps tool selection separate from model generation. The orchestrator:
 * 1. understands intent/domain metadata,
 * 2. builds an ordered tool plan,
 * 3. records fallback tools,
 * 4. never claims a tool ran unless the worker reports execution.
 *
 * All tools are free-only and side-effect free at the planning layer.
 */

const TOOL_DEFINITIONS = {
  weather: {
    id: 'weather',
    kind: 'specialized_data',
    domains: ['weather'],
    intents: ['weather', 'current_information'],
    priority: 100,
    fallbacks: ['web_search']
  },
  web_search: {
    id: 'web_search',
    kind: 'research',
    domains: ['research', 'finance', 'jobs', 'business', 'code', 'general'],
    intents: ['research', 'current_information', 'comparison', 'question'],
    priority: 80,
    fallbacks: []
  },
  calculator: {
    id: 'calculator',
    kind: 'deterministic',
    domains: ['math', 'finance', 'analysis', 'general'],
    intents: ['calculation', 'question'],
    priority: 110,
    fallbacks: ['model_reasoning']
  },
  code_reasoning: {
    id: 'code_reasoning',
    kind: 'reasoning',
    domains: ['code'],
    intents: ['code', 'question'],
    priority: 90,
    fallbacks: ['model_reasoning']
  },
  model_reasoning: {
    id: 'model_reasoning',
    kind: 'generation',
    domains: ['general'],
    intents: ['conversation', 'question', 'comparison', 'research', 'current_information', 'code'],
    priority: 10,
    fallbacks: []
  }
};

export function evaluateIntent({ language = {}, route = {}, message = '', context = {} } = {}) {
  const text = String(message || '').trim();
  const lower = text.toLowerCase();
  const domains = new Set((language.domains || []).map(item => item?.domain).filter(Boolean));
  const explicitMode = String(route?.mode || context?.mode || 'auto').toLowerCase();
  const signals = {
    current: /\b(hoy|ahora|actual(?:mente)?|últim[oa]s?|latest|news|noticias?|precio|cotización|cuánto cuesta|when|where|who)\b/i.test(lower),
    research: /\b(busca|buscar|investiga|fuentes|compara|comparar|contrasta|alternativas|opciones|search|research)\b/i.test(lower),
    calculation: /(?:cuánto es|calcula|calcular|calculate|compute|porcentaje|roi|\b\d+(?:[.,]\d+)?\s*[+*\/\-]\s*\d)/i.test(lower) || language.intent === 'calculation',
    code: language.intent === 'code' || domains.has('code') || /\b(código|code|python|javascript|sql|api|bug|error|github)\b/i.test(lower),
    comparison: language.intent === 'comparison' || /\b(compara|comparar|versus|\bvs\.?\b|diferencia|mejor que|alternativas)\b/i.test(lower),
    context_followup: Array.isArray(context?.references) && context.references.length > 0,
    long_or_complex: text.length > 240 || /\b(paso a paso|analiza|análisis|planifica|diseña|arquitectura|profundo|detalladamente|deep|complex)\b/i.test(lower)
  };
  let primaryIntent = String(language.intent || route.intent || 'question');
  if (signals.calculation) primaryIntent = 'calculation';
  else if (signals.code) primaryIntent = 'code';
  else if (signals.comparison) primaryIntent = 'comparison';
  else if (signals.current) primaryIntent = 'current_information';
  else if (signals.research) primaryIntent = 'research';
  else if (language.intent === 'conversation' || /^(hola|hi|hello|olá|oi|buenas?)\b/i.test(lower)) primaryIntent = 'conversation';

  let complexity = 'simple';
  if (signals.long_or_complex || signals.comparison || signals.context_followup) complexity = 'complex';
  else if (signals.current || signals.research || signals.calculation || signals.code) complexity = 'moderate';

  let toolNeed = 'none';
  if (signals.calculation) toolNeed = 'calculator';
  else if (domains.has('weather') || language.intent === 'weather') toolNeed = 'weather';
  else if (signals.code) toolNeed = 'code_reasoning';
  else if (signals.current || signals.research || signals.comparison) toolNeed = 'web_search';

  if (explicitMode === 'matemática' || explicitMode === 'math') toolNeed = 'calculator';
  if (explicitMode === 'código' || explicitMode === 'code') toolNeed = 'code_reasoning';
  if (explicitMode === 'investigación' || explicitMode === 'research') toolNeed = 'web_search';

  const activeSignals = Object.values(signals).filter(Boolean).length;
  const ambiguity = activeSignals >= 3 && !signals.long_or_complex ? 0.08 : 0;
  const confidence = Math.max(0.55, Math.min(0.99, 0.72 + activeSignals * 0.035 - ambiguity));
  const reasoningLevel = complexity === 'complex' ? 'deep' : complexity === 'moderate' ? 'standard' : 'fast';
  return {
    intent: primaryIntent,
    confidence,
    complexity,
    reasoning_level: reasoningLevel,
    tool_need: toolNeed,
    explicit_mode: explicitMode,
    signals,
    should_research: toolNeed === 'web_search',
    should_use_specialized_tool: toolNeed !== 'none',
    fallback_to_model: true
  };
}

export function selectTools({ language = {}, route = {}, message = '', context = {} } = {}) {
  const intentEval = evaluateIntent({ language, route, message, context });

  const domains = new Set((language.domains || []).map(item => item?.domain).filter(Boolean));
  const intent = String(intentEval.intent || language.intent || route.intent || 'question');
  const candidates = [];

  if (intent === 'weather' || domains.has('weather')) candidates.push('weather');
  if (isCalculation(message, intent, domains)) candidates.push('calculator');
  if (intent === 'code' || domains.has('code')) candidates.push('code_reasoning');

  const researchRequired = Boolean(route.research_required || intentEval.should_research);
  if (researchRequired || intent === 'research' || intent === 'comparison' || intent === 'current_information') {
    candidates.push('web_search');
  }

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

  return {
    primary,
    ordered: chain,
    fallbacks: chain.slice(1),
    selected: unique,
    reason: buildReason(primary, intent, domains),
    intent_evaluation: intentEval,
    tool_registry_version: '1.0'
  };
}

export function buildToolActivity(plan) {
  const primary = TOOL_DEFINITIONS[plan?.primary];
  if (!primary) return 'Análisis directo seleccionado.';
  const labels = {
    weather: 'Consulta meteorológica verificada iniciada.',
    web_search: 'Búsqueda web seleccionada para recopilar evidencia.',
    calculator: 'Cálculo determinista seleccionado.',
    code_reasoning: 'Análisis de código seleccionado.',
    model_reasoning: 'Razonamiento directo seleccionado.'
  };
  return labels[primary.id] || 'Herramienta seleccionada según la intención.';
}

export function toolLabel(id) {
  return ({
    weather: 'meteorología',
    web_search: 'búsqueda web',
    calculator: 'cálculo',
    code_reasoning: 'análisis de código',
    model_reasoning: 'razonamiento'
  })[id] || String(id || 'herramienta');
}

function isCalculation(message, intent, domains) {
  if (intent === 'calculation') return true;
  if (domains.has('math')) return true;
  return /(?:cu[aá]nto es|calcula|calcular|calculate|compute|suma|resta|multiplica|divide|porcentaje|%|\b\d+(?:[.,]\d+)?\s*[+*\/\-]\s*\d)/i.test(String(message || ''));
}

function buildReason(primary, intent, domains) {
  if (primary === 'weather') return 'weather_intent';
  if (primary === 'calculator') return 'deterministic_calculation';
  if (primary === 'code_reasoning') return 'code_domain';
  if (primary === 'web_search') return domains.size ? 'external_evidence_required_for_domain' : 'research_or_current_information';
  return intent === 'conversation' ? 'conversation' : 'direct_reasoning';
}

export function getToolRegistry() {
  return Object.values(TOOL_DEFINITIONS).map(tool => ({
    id: tool.id,
    kind: tool.kind,
    domains: tool.domains,
    intents: tool.intents,
    priority: tool.priority,
    fallbacks: tool.fallbacks
  }));
}

/**
 * Build a multi-tool execution plan for compound requests.
 * The plan is declarative: execution must be confirmed by the worker.
 */
export function buildCompoundPlan({ language = {}, route = {}, message = '', context = {} } = {}) {
  const base = selectTools({ language, route, message, context });
  const text = String(message || '').toLowerCase();
  const steps = [];
  const add = (tool, purpose) => {
    if (!steps.some(step => step.tool === tool)) steps.push({ order: steps.length + 1, tool, purpose });
  };

  if (base.primary === 'weather') add('weather', 'obtener datos meteorológicos actuales');
  if (base.selected.includes('web_search') || route.research_required) add('web_search', 'recopilar y contrastar evidencia externa');
  if (base.selected.includes('calculator') || language.intent === 'calculation') add('calculator', 'realizar cálculos deterministas');
  if (base.selected.includes('code_reasoning') || language.intent === 'code') add('code_reasoning', 'analizar código y resultados técnicos');

  const compoundSignals = /\b(compara|comparar|comparativa|contrasta|calcula|cu[aá]nto|coste|costo|precio|inversi[oó]n|recuperar|roi|entre|versus|vs\.?)\b/i.test(text);
  if (compoundSignals && steps.length < 2) {
    add('web_search', 'obtener evidencia para la comparación');
    add('calculator', 'calcular magnitudes derivadas');
  }

  if (!steps.length) add('model_reasoning', 'sintetizar la respuesta con razonamiento directo');

  return {
    ...base,
    compound: steps.length > 1,
    steps,
    execution_policy: 'execute_in_order_and_report_actual_results'
  };
}
