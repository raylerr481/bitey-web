const DEFAULT_LIMIT = 10000;
const MODEL = '@cf/google/gemma-4-26b-a4b-it';
const INPUT_NEURONS_PER_MILLION = 9091;
const OUTPUT_NEURONS_PER_MILLION = 27273;
const ledger = new Map();

function dayKey(now = Date.now()) {
  return new Date(now).toISOString().slice(0, 10);
}

function estimateTokens(value) {
  const text = typeof value === 'string' ? value : JSON.stringify(value ?? '');
  return Math.max(1, Math.ceil(text.length / 4));
}

function estimateNeurons(model, params) {
  if (model !== MODEL) return Number.POSITIVE_INFINITY;
  const messages = Array.isArray(params?.messages) ? params.messages : [];
  const inputTokens = estimateTokens(messages);
  const outputTokens = Math.max(1, Number(params?.max_tokens || 256));
  return Math.ceil(
    (inputTokens * INPUT_NEURONS_PER_MILLION + outputTokens * OUTPUT_NEURONS_PER_MILLION) / 1_000_000
  );
}

function state(limit = DEFAULT_LIMIT) {
  const key = dayKey();
  const used = ledger.get(key) || 0;
  return { day: key, limit, used, remaining: Math.max(0, limit - used), blocked: used >= limit };
}

function reserve(model, params, limit = DEFAULT_LIMIT) {
  const estimate = estimateNeurons(model, params);
  if (!Number.isFinite(estimate)) {
    return { allowed: false, reason: 'model_not_allowed_zero_cost', estimate, ...state(limit) };
  }
  const current = state(limit);
  if (current.used + estimate > limit) {
    return { allowed: false, reason: 'daily_neuron_limit', estimate, ...current };
  }
  ledger.set(current.day, current.used + estimate);
  return { allowed: true, reason: 'within_daily_limit', estimate, ...state(limit) };
}

export function createZeroCostAi(ai, limit = DEFAULT_LIMIT) {
  if (!ai || typeof ai.run !== 'function') return ai;
  return {
    async run(model, params) {
      const reservation = reserve(model, params, limit);
      if (!reservation.allowed) {
        const error = new Error(`Bitey Zero-Cost Guard blocked Workers AI: ${reservation.reason}`);
        error.code = 'BITEY_ZERO_COST_LIMIT';
        error.guard = reservation;
        throw error;
      }
      return ai.run(model, params);
    }
  };
}

export function zeroCostStatus(limit = DEFAULT_LIMIT) {
  return {
    mode: 'ZERO_COST_BY_DEFAULT',
    provider: 'cloudflare-workers-ai',
    model: MODEL,
    daily_neuron_limit: limit,
    ...state(limit),
    enforcement: 'fail_closed_before_ai_run',
    note: 'Bitey-side estimate/reservation. Cloudflare remains the authoritative daily Neuron meter.'
  };
}
