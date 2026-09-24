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

export function selectTools({ language = {}, route = {}, message = '' } = {}) {
  const domains = new Set((language.domains || []).map(item => item?.domain).filter(Boolean));
  const intent = String(language.intent || route.intent || 'question');
  const candidates = [];

  if (intent === 'weather' || domains.has('weather')) candidates.push('weather');
  if (isCalculation(message, intent, domains)) candidates.push('calculator');
  if (intent === 'code' || domains.has('code')) candidates.push('code_reasoning');

  const researchRequired = Boolean(route.research_required);
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
  return /(?:cu[aá]nto es|calcula|calcular|calculate|compute|suma|resta|multiplica|divide|porcentaje|%|\\b\\d+(?:[.,]\\d+)?\\s*[+*\\/\\-]\\s*\\d)/i.test(String(message || ''));
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
