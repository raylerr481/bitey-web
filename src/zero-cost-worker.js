import biteyWorker from './capability-worker.js';
import { providerStatus, createProviderAi } from './provider-gateway.js';

const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' };

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const baseAi = createProviderAi(env);
    let lastProvider = null;
    let lastModel = null;
    const providerAi = {
      ...baseAi,
      async run(...args) {
        const response = await baseAi.run(...args);
        lastProvider = response?.provider || null;
        lastModel = response?.model || null;
        return response;
      },
    };

    if (url.pathname === '/api/diagnostics/providers' && request.method === 'GET') {
      return new Response(JSON.stringify({ ok: true, ...providerStatus(env) }), { status: 200, headers: JSON_HEADERS });
    }

    if (url.pathname === '/api/diagnostics/edge-ai' && request.method === 'GET') {
      try {
        const response = await providerAi.run('diagnostic', {
          messages: [
            { role: 'system', content: 'Responde únicamente con el resultado de la operación solicitada.' },
            { role: 'user', content: '¿Cuánto es 2+2?' },
          ],
          max_tokens: 32,
          temperature: 0,
        });
        return new Response(JSON.stringify({
          ok: true,
          selected_provider: response?.provider || lastProvider,
          model: response?.model || lastModel,
          answer: response?.response || '',
          policy: 'qwen-primary-groq-fallback',
        }), { status: 200, headers: JSON_HEADERS });
      } catch (error) {
        if (error?.code === 'BITEY_PROVIDER_UNAVAILABLE') {
          return new Response(JSON.stringify({ ok: false, error: 'ai_provider_unavailable', policy: 'qwen-primary-groq-fallback', providers: error.providers || [] }), { status: 503, headers: JSON_HEADERS });
        }
        throw error;
      }
    }

    const providerEnv = { ...env, AI: providerAi };
    try {
      const response = await biteyWorker.fetch(request, providerEnv, ctx);
      if (isPublicConversationMessage(request, response)) {
        return await generatePublicAnswerWithProvider(response, request, providerAi);
      }
      return await normalizeLegacyProviderMetadata(response, lastProvider, lastModel);
    } catch (error) {
      if (error?.code === 'BITEY_PROVIDER_UNAVAILABLE') {
        return new Response(JSON.stringify({
          error: 'ai_provider_unavailable',
          message: 'Bitey no tiene un proveedor de IA disponible en este momento.',
          provider_policy: 'qwen-primary-groq-fallback',
          providers: error.providers || [],
        }), { status: 503, headers: { ...JSON_HEADERS, 'X-Bitey-Provider': 'unavailable' } });
      }
      throw error;
    }
  }
};

function isPublicConversationMessage(request, response) {
  const url = new URL(request.url);
  if (request.method !== 'POST' || !url.pathname.includes('/conversations/') || !url.pathname.endsWith('/messages')) return false;
  if (response?.headers.get('X-Bitey-Delegated') === 'true') return false;
  return true;
}

async function generatePublicAnswerWithProvider(upstream, request, providerAi) {
  let payload;
  try { payload = await request.clone().json(); } catch (_) { return upstream; }
  const userMessage = String(payload?.message || '').trim();
  if (!userMessage) return upstream;

  let backendBody = {};
  try { backendBody = await upstream.clone().json(); } catch (_) {}
  const backendAnswer = String(backendBody?.answer || '').trim();
  const sources = Array.isArray(backendBody?.sources) ? backendBody.sources : [];
  const evidence = String(backendBody?.evidence_context || '').trim();
  const context = [
    backendAnswer ? `CONTEXTO PREVIO DEL CEREBRO BITEY:\n${backendAnswer}` : '',
    evidence ? `EVIDENCIA DEL CEREBRO BITEY:\n${evidence}` : '',
    sources.length ? `FUENTES DEL CEREBRO BITEY:\n${sources.map((s, i) => `[${i + 1}] ${s.title || s.url || 'Fuente'} — ${s.url || ''}`).join('\n')}` : '',
  ].filter(Boolean).join('\n\n').slice(0, 12000);

  const messages = [
    { role: 'system', content: 'Eres Bitey IA, una inteligencia general pública. Responde en el idioma del usuario. Sé útil, clara y directa. Usa el contexto y evidencia proporcionados cuando sean relevantes. No inventes datos. No expongas nombres de proveedores, capas internas, contratos ni diagnósticos.' },
    ...(context ? [{ role: 'system', content: context }] : []),
    { role: 'user', content: userMessage },
  ];

  let generated;
  try {
    generated = await providerAi.run('public-chat', { messages, max_tokens: 768, temperature: 0.2 });
  } catch (error) {
    if (error?.code === 'BITEY_PROVIDER_UNAVAILABLE') {
      return new Response(JSON.stringify({
        ...backendBody,
        answer: 'Ahora mismo no puedo completar esta consulta. Inténtalo nuevamente en unos momentos.',
        error: 'ai_provider_unavailable',
        provider_policy: 'qwen-primary-groq-fallback',
        providers: error.providers || [],
        selected_provider: null,
      }), { status: 503, headers: { ...JSON_HEADERS, 'X-Bitey-Provider': 'unavailable' } });
    }
    throw error;
  }

  const merged = {
    ...backendBody,
    answer: generated?.response || backendAnswer,
    providers: generated?.provider ? [generated.provider] : [],
    selected_provider: generated?.provider || null,
    model: generated?.model || null,
    provider_policy: 'qwen-primary-groq-fallback',
    activity_events: [
      ...(Array.isArray(backendBody?.activity_events) ? backendBody.activity_events : []),
      `Respuesta generada por el proveedor seleccionado: ${generated?.provider || 'unknown'}.`,
    ],
  };
  const headers = new Headers(upstream.headers);
  headers.set('content-type', 'application/json; charset=utf-8');
  headers.set('cache-control', 'no-store');
  headers.set('X-Bitey-Provider', generated?.provider || 'unknown');
  if (generated?.model) headers.set('X-Bitey-Model', generated.model);
  headers.set('X-Bitey-Provider-Policy', 'qwen-primary-groq-fallback');
  return new Response(JSON.stringify(merged), { status: 200, headers });
}

async function normalizeLegacyProviderMetadata(response, provider, model) {
  if (!response || !provider || !response.headers.get('content-type')?.includes('application/json')) return response;
  try {
    const payload = await response.clone().json();
    if (payload?.selected_provider !== 'cloudflare-workers-ai' && payload?.providers?.[0] !== '@cf/google/gemma-4-26b-a4b-it') return response;
    payload.selected_provider = provider;
    if (model) payload.model = model;
    if (Array.isArray(payload.providers)) payload.providers = [provider];
    if (Array.isArray(payload.activity_events)) {
      payload.activity_events = payload.activity_events.map(event => String(event)
        .replace(/Cloudflare Workers AI/gi, provider)
        .replace(/Cloudflare/gi, provider));
    }
    const headers = new Headers(response.headers);
    headers.set('content-type', 'application/json; charset=utf-8');
    headers.set('cache-control', 'no-store');
    headers.set('X-Bitey-Provider', provider);
    if (model) headers.set('X-Bitey-Model', model);
    return new Response(JSON.stringify(payload), { status: response.status, statusText: response.statusText, headers });
  } catch (_) {
    return response;
  }
}
