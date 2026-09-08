import biteyWorker from './capability-worker.js';
import { providerStatus, createProviderAi } from './provider-gateway.js';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === '/api/diagnostics/providers' && request.method === 'GET') {
      return new Response(JSON.stringify({ ok: true, ...providerStatus(env) }), { status: 200, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
    }

    const providerEnv = { ...env, AI: createProviderAi(env) };
    try {
      return await biteyWorker.fetch(request, providerEnv, ctx);
    } catch (error) {
      if (error?.code === 'BITEY_PROVIDER_UNAVAILABLE') {
        return new Response(JSON.stringify({
          error: 'ai_provider_unavailable',
          message: 'Bitey no tiene un proveedor de IA disponible en este momento.',
          provider_policy: 'qwen-primary-groq-fallback',
          providers: error.providers || [],
        }), { status: 503, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'X-Bitey-Provider': 'unavailable' } });
      }
      throw error;
    }
  }
};
