import biteyWorker from './capability-worker.js';
import { createZeroCostAi, zeroCostStatus } from './zero-cost-guard.js';

const DEFAULT_LIMIT = 10000;
function limitFromEnv(env) { const parsed = Number(env?.BITEY_DAILY_NEURON_LIMIT || DEFAULT_LIMIT); return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : DEFAULT_LIMIT; }
export default {
  async fetch(request, env, ctx) {
    const limit = limitFromEnv(env);
    const url = new URL(request.url);
    if (url.pathname === '/api/diagnostics/zero-cost' && request.method === 'GET') return new Response(JSON.stringify({ ok: true, ...zeroCostStatus(limit) }), { status: 200, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
    const guardedEnv = env.AI ? { ...env, AI: createZeroCostAi(env.AI, limit) } : env;
    try { return await biteyWorker.fetch(request, guardedEnv, ctx); }
    catch (error) {
      if (error?.code === 'BITEY_ZERO_COST_LIMIT') return new Response(JSON.stringify({ error: 'workers_ai_daily_limit_reached', message: 'Bitey detuvo esta operación para mantener el modo cero costos. Workers AI volverá a estar disponible cuando se renueve la cuota diaria.', zero_cost: true, guard: error.guard || zeroCostStatus(limit) }), { status: 429, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'X-Bitey-Zero-Cost': 'blocked' } });
      throw error;
    }
  }
};
