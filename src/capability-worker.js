import biteyWorker from './skills-worker.js';
import { shouldDelegate, mergeCapabilityResult } from './capability-router.js';
import { delegateCapability, specializedUnavailable } from './capability-contract.js';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method !== 'POST' || !url.pathname.match(/\/api\/v1\/conversations\/[^/]+\/messages$/)) return biteyWorker.fetch(request, env, ctx);
    let payload;
    try { payload = await request.clone().json(); } catch (_) { return biteyWorker.fetch(request, env, ctx); }
    const message = String(payload?.message || '').trim();
    const route = shouldDelegate(message, request.headers);
    if (!route.delegate) return biteyWorker.fetch(request, env, ctx);
    const conversationId = url.pathname.match(/\/conversations\/([^/]+)\/messages$/)?.[1] || '';
    const requestId = request.headers.get('x-request-id') || crypto.randomUUID();
    const result = await delegateCapability({ request, env, requestId, capability: route.capability, message, conversationId });
    if (!result.handled) {
      const status = result.configured ? 502 : 503;
      return new Response(JSON.stringify(specializedUnavailable(route.capability, result.reason, requestId)), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'X-Bitey-Capability': route.capability, 'X-Bitey-Delegated': 'false', 'X-Bitey-Request-Id': requestId } });
    }
    const body = mergeCapabilityResult({
      ...result.body,
      conversation_id: result.body?.conversation_id || conversationId,
      delegated: true,
      delegation_status: 'accepted',
      request_id: requestId,
      cognitive_route: result.body?.cognitive_route || {
        intent: 'specialized',
        capability: route.capability,
        research_attempted: Boolean(result.body?.research_attempted || result.body?.sources?.length),
        research_required: Boolean(result.body?.research_required || result.body?.sources?.length),
        comparison_required: Boolean(result.body?.comparison_required),
        evidence_method: result.body?.evidence_method || 'specialized-capability',
        reasons: ['specialized_capability_routing']
      },
      activity_events: [
        'Intención especializada identificada.',
        'Capacidad ' + route.capability + ' seleccionada.',
        ...(Array.isArray(result.body?.activity_events) ? result.body.activity_events : []),
        'Resultado especializado verificado antes de entregarlo.'
      ]
    }, route.capability);
    return new Response(JSON.stringify(body), { status: result.status || 200, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'X-Bitey-Capability': route.capability, 'X-Bitey-Delegated': 'true', 'X-Bitey-Request-Id': requestId } });
  }
};
