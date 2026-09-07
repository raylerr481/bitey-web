import biteyWorker from './skills-worker.js';
import { shouldDelegate, mergeCapabilityResult } from './capability-router.js';
import { delegateCapability, specializedUnavailable } from './capability-contract.js';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method !== 'POST' || !url.pathname.match(/\/api\/v1\/conversations\/[^/]+\/messages$/)) {
      return biteyWorker.fetch(request, env, ctx);
    }
    const capability = shouldDelegate('', request.headers);
    if (!capability.specialized || !capability.delegate) return biteyWorker.fetch(request, env, ctx);
    let payload;
    try { payload = await request.clone().json(); } catch (_) { return biteyWorker.fetch(request, env, ctx); }
    const message = String(payload?.message || '').trim();
    const route = shouldDelegate(message, request.headers);
    if (!route.delegate) return biteyWorker.fetch(request, env, ctx);
    const conversationId = url.pathname.match(/\/conversations\/([^/]+)\/messages$/)?.[1] || '';
    const requestId = request.headers.get('x-request-id') || crypto.randomUUID();
    const result = await delegateCapability({ request, env, requestId, capability: route.capability, message, conversationId });
    if (!result.handled) {
      if (!result.configured) {
        return new Response(JSON.stringify(specializedUnavailable(route.capability, result.reason, requestId)), { status: 503, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'X-Bitey-Capability': route.capability, 'X-Bitey-Delegated': 'false', 'X-Bitey-Request-Id': requestId } });
      }
      return new Response(JSON.stringify(specializedUnavailable(route.capability, result.reason, requestId)), { status: 502, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'X-Bitey-Capability': route.capability, 'X-Bitey-Delegated': 'false', 'X-Bitey-Request-Id': requestId } });
    }
    const body = mergeCapabilityResult({ ...result.body, conversation_id: result.body?.conversation_id || conversationId, delegated: true, delegation_status: 'accepted', request_id: requestId }, route.capability);
    return new Response(JSON.stringify(body), { status: result.status || 200, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'X-Bitey-Capability': route.capability, 'X-Bitey-Delegated': 'true', 'X-Bitey-Request-Id': requestId } });
  }
};
