const DEFAULT_QWEN_MODEL = 'qwen-plus';
const DEFAULT_QWEN_BASE_URL = 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1';
const DEFAULT_GROQ_MODEL = 'qwen/qwen3.6-27b';
const DEFAULT_GROQ_BASE_URL = 'https://api.groq.com/openai/v1';

export function createProviderAi(env) {
  return {
    async run(_model, input = {}) {
      const messages = Array.isArray(input.messages) ? input.messages : [];
      const maxTokens = Number(input.max_tokens || 512);
      const temperature = Number.isFinite(Number(input.temperature)) ? Number(input.temperature) : 0.2;
      const errors = [];

      const qwen = await callOpenAiCompatible({
        provider: 'qwen',
        apiKey: env.QWEN_API_KEY || env.DASHSCOPE_API_KEY,
        baseUrl: env.QWEN_BASE_URL || DEFAULT_QWEN_BASE_URL,
        model: env.QWEN_MODEL || DEFAULT_QWEN_MODEL,
        messages,
        maxTokens,
        temperature,
      });
      if (qwen.ok) return qwen.response;
      errors.push(qwen.error);

      const groqEnabled = String(env.GROQ_ENABLED || 'true').toLowerCase() !== 'false';
      if (groqEnabled) {
        const groq = await callOpenAiCompatible({
          provider: 'groq',
          apiKey: env.GROQ_API_KEY,
          baseUrl: env.GROQ_BASE_URL || DEFAULT_GROQ_BASE_URL,
          model: env.GROQ_MODEL || DEFAULT_GROQ_MODEL,
          messages,
          maxTokens,
          temperature,
        });
        if (groq.ok) return groq.response;
        errors.push(groq.error);
      }

      const error = new Error('No configured AI provider completed the request');
      error.code = 'BITEY_PROVIDER_UNAVAILABLE';
      error.providers = errors.map(item => ({ provider: item.provider, status: item.status, message: item.message }));
      throw error;
    },
  };
}

export function providerStatus(env) {
  return {
    qwen: {
      configured: Boolean(env.QWEN_API_KEY || env.DASHSCOPE_API_KEY),
      model: env.QWEN_MODEL || DEFAULT_QWEN_MODEL,
      base_url: env.QWEN_BASE_URL || DEFAULT_QWEN_BASE_URL,
      base_url_configured: true,
    },
    groq: {
      configured: Boolean(env.GROQ_API_KEY),
      enabled: String(env.GROQ_ENABLED || 'true').toLowerCase() !== 'false',
      model: env.GROQ_MODEL || DEFAULT_GROQ_MODEL,
      base_url: env.GROQ_BASE_URL || DEFAULT_GROQ_BASE_URL,
    },
    policy: 'qwen-primary-groq-fallback',
  };
}

async function callOpenAiCompatible({ provider, apiKey, baseUrl, model, messages, maxTokens, temperature }) {
  if (!apiKey) return { ok: false, error: { provider, status: 0, message: 'api_key_not_configured' } };
  if (!baseUrl) return { ok: false, error: { provider, status: 0, message: 'base_url_not_configured' } };
  const endpoint = `${String(baseUrl).replace(/\/$/, '')}/chat/completions`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      signal: controller.signal,
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, messages, max_tokens: maxTokens, temperature }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) return { ok: false, error: { provider, status: response.status, message: String(body?.error?.message || body?.message || 'provider_error') } };
    const text = String(body?.choices?.[0]?.message?.content || body?.output?.[0]?.content?.[0]?.text || '').trim();
    if (!text) return { ok: false, error: { provider, status: response.status, message: 'empty_response' } };
    return { ok: true, response: { response: text, provider, model } };
  } catch (error) {
    return { ok: false, error: { provider, status: 0, message: error?.name === 'AbortError' ? 'timeout' : String(error) } };
  } finally {
    clearTimeout(timer);
  }
}
