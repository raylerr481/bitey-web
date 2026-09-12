import biteyWorker from './capability-worker.js';
import { providerStatus, createProviderAi } from './provider-gateway.js';

const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' };
const PROVIDER_POLICY = 'groq-primary-free-only';

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
      return new Response(JSON.stringify({
        ok: true,
        ...providerStatus(env),
        authority: 'bitey-ia-backend',
        policy: PROVIDER_POLICY,
      }), { status: 200, headers: JSON_HEADERS });
    }

    if (url.pathname === '/api/diagnostics/edge-ai' && request.method === 'GET') {
      try {
        const response = await providerAi.run('diagnostic', {
          messages: [
            { role: 'system', content: 'Responde únicamente con el resultado de la operación solicitada. No muestres razonamiento interno.' },
            { role: 'user', content: '¿Cuánto es 2+2?' },
          ],
          max_tokens: 32,
          temperature: 0,
        });
        return new Response(JSON.stringify(sanitizePublicPayload({
          ok: true,
          selected_provider: response?.provider || lastProvider,
          model: response?.model || lastModel,
          answer: response?.response || '',
          policy: PROVIDER_POLICY,
          note: 'Diagnostic endpoint only; public conversations remain backend-authoritative.',
        })), { status: 200, headers: JSON_HEADERS });
      } catch (error) {
        if (error?.code === 'BITEY_PROVIDER_UNAVAILABLE') {
          return new Response(JSON.stringify({ ok: false, error: 'ai_provider_unavailable', policy: PROVIDER_POLICY, providers: error.providers || [] }), { status: 503, headers: JSON_HEADERS });
        }
        throw error;
      }
    }

    const providerEnv = { ...env, AI: providerAi };
    try {
      const response = await biteyWorker.fetch(request, providerEnv, ctx);
      return await normalizePublicResponse(response, lastProvider, lastModel);
    } catch (error) {
      if (error?.code === 'BITEY_PROVIDER_UNAVAILABLE') {
        return new Response(JSON.stringify({
          error: 'ai_provider_unavailable',
          message: 'Bitey no tiene un proveedor de IA gratuito disponible en este momento.',
          provider_policy: PROVIDER_POLICY,
          providers: error.providers || [],
        }), { status: 503, headers: { ...JSON_HEADERS, 'X-Bitey-Provider': 'unavailable' } });
      }
      throw error;
    }
  }
};

async function normalizePublicResponse(response, provider, model) {
  if (!response || !response.headers.get('content-type')?.includes('application/json')) return response;
  try {
    const payload = sanitizePublicPayload(await response.clone().json());
    const legacyCloudflare = payload?.selected_provider === 'cloudflare-workers-ai' || payload?.providers?.[0] === '@cf/google/gemma-4-26b-a4b-it';
    const backendGroqAlias = payload?.selected_provider === 'groq-free' || (Array.isArray(payload?.providers) && payload.providers.includes('groq-free'));
    if (legacyCloudflare) {
      payload.selected_provider = provider || payload.selected_provider;
      if (model) payload.model = model;
      if (Array.isArray(payload.providers)) payload.providers = [payload.selected_provider];
      if (Array.isArray(payload.activity_events)) {
        payload.activity_events = payload.activity_events.map(event => String(event)
          .replace(/Cloudflare Workers AI/gi, payload.selected_provider || 'groq')
          .replace(/Cloudflare/gi, payload.selected_provider || 'groq'));
      }
    } else if (backendGroqAlias) {
      payload.selected_provider = 'groq';
      if (Array.isArray(payload.providers)) payload.providers = payload.providers.map(name => name === 'groq-free' ? 'groq' : name);
    }
    const headers = new Headers(response.headers);
    headers.set('content-type', 'application/json; charset=utf-8');
    headers.set('cache-control', 'no-store');
    headers.set('X-Bitey-Provider', payload.selected_provider || provider || 'backend');
    if (model) headers.set('X-Bitey-Model', model);
    headers.set('X-Bitey-Provider-Policy', PROVIDER_POLICY);
    return new Response(JSON.stringify(payload), { status: response.status, statusText: response.statusText, headers });
  } catch (_) {
    return response;
  }
}

function sanitizePublicPayload(value) {
  if (typeof value === 'string') return sanitizePublicText(value);
  if (Array.isArray(value)) return value.map(sanitizePublicPayload);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, sanitizePublicPayload(item)]));
  }
  return value;
}

function sanitizePublicText(text) {
  return String(text)
    .replace(/<think>[\s\S]*?<\/think>/gi, '')
    .replace(/<analysis>[\s\S]*?<\/analysis>/gi, '')
    .replace(/<reasoning>[\s\S]*?<\/reasoning>/gi, '')
    .replace(/&lt;think&gt;[\s\S]*?&lt;\/think&gt;/gi, '')
    .replace(/&lt;analysis&gt;[\s\S]*?&lt;\/analysis&gt;/gi, '')
    .replace(/&lt;reasoning&gt;[\s\S]*?&lt;\/reasoning&gt;/gi, '')
    .replace(/<\/?(?:think|analysis|reasoning)>/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}
