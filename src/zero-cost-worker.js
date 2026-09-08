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
