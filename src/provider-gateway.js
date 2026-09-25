const DEFAULT_GROQ_MODEL = 'openai/gpt-oss-120b';
const DEFAULT_GROQ_BASE_URL = 'https://api.groq.com/openai/v1';
const DEFAULT_OPENROUTER_MODEL = 'nvidia/nemotron-3-ultra-550b-a55b:free';
const DEFAULT_OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1';
const FREE_PROVIDERS = new Set(['groq', 'openrouter']);

export function createProviderAi(env) {
  return {
    async run(_model, input = {}) {
      const result = await runFreeProviderChain(env, input);
      if (result.ok) return result.response;
      throw providerUnavailable(result.errors);
    },
    async runTeachers(input = {}) {
      return runTeacherEnsemble(env, input);
    }
  };
}

export async function runFreeProviderChain(env, input = {}) {
  const messages = Array.isArray(input.messages) ? input.messages : [];
  const maxTokens = Number(input.max_tokens || 512);
  const temperature = Number.isFinite(Number(input.temperature)) ? Number(input.temperature) : 0.2;
  const order = String(env.BITEY_PROVIDER_ORDER || 'groq,openrouter')
    .split(',').map(value => value.trim().toLowerCase())
    .filter(provider => FREE_PROVIDERS.has(provider));
  const errors = [];
  for (const provider of order) {
    const result = await callProvider(provider, env, { messages, maxTokens, temperature });
    if (result.ok) return result;
    errors.push(result.error);
  }
  return { ok: false, errors };
}

export async function runTeacherEnsemble(env, input = {}) {
  const messages = Array.isArray(input.messages) ? input.messages : [];
  const maxTokens = Math.min(Number(input.max_tokens || 512), 768);
  const temperature = Number.isFinite(Number(input.temperature)) ? Number(input.temperature) : 0.1;
  const teachers = [];
  for (const provider of ['groq', 'openrouter']) {
    const result = await callProvider(provider, env, { messages, maxTokens, temperature });
    if (result.ok) teachers.push(result.response);
  }
  return {
    teachers,
    consensus: selectTeacherConsensus(teachers, input.sources || []),
    trained: teachers.length >= 1,
    teacher_count: teachers.length,
    providers: teachers.map(item => item.provider)
  };
}

export function providerStatus(env) {
  return {
    groq: {
      configured: Boolean(env.GROQ_API_KEY),
      enabled: String(env.GROQ_ENABLED || 'true').toLowerCase() !== 'false',
      model: env.GROQ_MODEL || DEFAULT_GROQ_MODEL,
      base_url: env.GROQ_BASE_URL || DEFAULT_GROQ_BASE_URL,
      cost_mode: 'free-only'
    },
    openrouter: {
      configured: Boolean(env.OPENROUTER_API_KEY),
      enabled: String(env.OPENROUTER_ENABLED || 'true').toLowerCase() !== 'false',
      model: env.OPENROUTER_MODEL || DEFAULT_OPENROUTER_MODEL,
      base_url: env.OPENROUTER_BASE_URL || DEFAULT_OPENROUTER_BASE_URL,
      cost_mode: 'free-only'
    },
    policy: 'groq-openrouter-free-only-no-paid-fallback',
    teacher_mode: String(env.BITEY_TEACHER_MODE || 'auto')
  };
}

async function callProvider(provider, env, options) {
  if (!FREE_PROVIDERS.has(provider)) return { ok: false, error: { provider, status: 0, message: 'provider_not_allowed' } };
  if (String(env[`${provider.toUpperCase()}_ENABLED`] || 'true').toLowerCase() === 'false') {
    return { ok: false, error: { provider, status: 0, message: 'provider_disabled' } };
  }
  const config = provider === 'groq'
    ? { apiKey: env.GROQ_API_KEY, baseUrl: env.GROQ_BASE_URL || DEFAULT_GROQ_BASE_URL, model: env.GROQ_MODEL || DEFAULT_GROQ_MODEL }
    : { apiKey: env.OPENROUTER_API_KEY, baseUrl: env.OPENROUTER_BASE_URL || DEFAULT_OPENROUTER_BASE_URL, model: env.OPENROUTER_MODEL || DEFAULT_OPENROUTER_MODEL };
  return callOpenAiCompatible({ provider, ...config, ...options });
}

function selectTeacherConsensus(teachers, sources = []) {
  if (!teachers.length) return null;
  if (teachers.length === 1) return { ...teachers[0], agreement_score: 0.5, judge: 'single-teacher' };
  const ranked = teachers.map(candidate => {
    const others = teachers.filter(item => item !== candidate);
    const agreement = others.reduce((sum, item) => (
      sum + tokenOverlap(normalizeForComparison(candidate.response), normalizeForComparison(item.response))
    ), 0) / others.length;
    const completeness = Math.min(1, Math.max(0.2, String(candidate.response || '').length / 900));
    const evidence = sources.length ? evidenceSupport(candidate.response, sources) : 0.5;
    const score = Number((agreement * 0.45 + evidence * 0.35 + completeness * 0.20).toFixed(3));
    return { candidate, agreement, evidence, score };
  }).sort((a, b) => b.score - a.score);
  const winner = ranked[0];
  const conflict = candidates.length > 1 && winner.agreement < 0.12;
  return {
    response: conflict ? '' : winner.candidate.response,
    provider: conflict ? 'teacher-conflict' : (winner.agreement >= 0.18 ? 'teacher-consensus' : winner.candidate.provider),
    agreement_score: winner.agreement,
    judge_score: winner.score,
    judge: 'agreement-evidence-completeness',
    conflict,
    requires_replan: conflict,
    evidence_score: winner.evidence,
    candidates: ranked.map(item => ({
      provider: item.candidate.provider,
      model: item.candidate.model,
      agreement_score: item.agreement,
      judge_score: item.score,
      evidence_score: item.evidence
    }))
  };
}

function evidenceSupport(text, sources) {
  const sourceText = sources.map(source => `${source.title || ''} ${source.url || ''} ${source.snippet || ''}`).join(' ');
  return Math.min(1, 0.45 + tokenOverlap(normalizeForComparison(text), normalizeForComparison(sourceText)) * 0.55);
}

function normalizeForComparison(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9áéíóúüñ\s]/gi, ' ')
    .split(/\s+/).filter(token => token.length > 3).slice(0, 250);
}

function tokenOverlap(a, b) {
  if (!a.length || !b.length) return 0;
  const setA = new Set(a), setB = new Set(b);
  let shared = 0;
  for (const token of setA) if (setB.has(token)) shared += 1;
  return shared / Math.max(setA.size, setB.size);
}

function providerUnavailable(errors) {
  const error = new Error('No configured free AI provider completed the request');
  error.code = 'BITEY_PROVIDER_UNAVAILABLE';
  error.providers = errors;
  return error;
}

async function callOpenAiCompatible({ provider, apiKey, baseUrl, model, messages, maxTokens, temperature }) {
  if (!apiKey) return { ok: false, error: { provider, status: 0, message: 'api_key_not_configured' } };
  if (!baseUrl) return { ok: false, error: { provider, status: 0, message: 'base_url_not_configured' } };
  if (provider === 'openrouter' && !String(model).endsWith(':free')) {
    return { ok: false, error: { provider, status: 0, message: 'free_model_required' } };
  }
  const endpoint = `${String(baseUrl).replace(/\/$/, '')}/chat/completions`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const headers = { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' };
    if (provider === 'openrouter') {
      headers['HTTP-Referer'] = 'https://bitey-web.raylerr481.workers.dev/';
      headers['X-Title'] = 'Bitey IA';
    }
    const response = await fetch(endpoint, {
      method: 'POST', signal: controller.signal, headers,
      body: JSON.stringify({ model, messages, max_tokens: maxTokens, temperature })
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) return { ok: false, error: { provider, status: response.status, message: String(body?.error?.message || body?.message || 'provider_error') } };
    const text = String(body?.choices?.[0]?.message?.content || body?.output?.[0]?.content?.[0]?.text || '').trim();
    if (!text) return { ok: false, error: { provider, status: response.status, message: 'empty_response' } };
    return { ok: true, response: { response: text, provider, model, cost_mode: 'free-only' } };
  } catch (error) {
    return { ok: false, error: { provider, status: 0, message: error?.name === 'AbortError' ? 'timeout' : String(error) } };
  } finally {
    clearTimeout(timer);
  }
}
