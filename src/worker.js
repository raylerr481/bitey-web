const AI_MODEL = '@cf/google/gemma-4-26b-a4b-it';
const NO_PROVIDER_ANSWER = 'Ahora mismo no puedo completar esta consulta. Inténtalo nuevamente en unos momentos.';
const LEGACY_NO_PROVIDER_ANSWER = 'No pude obtener una respuesta de Bitey IA en este momento. Inténtalo nuevamente en unos momentos.';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const requestId = request.headers.get('x-request-id') || crypto.randomUUID();

    if (url.pathname === '/api/diagnostics/edge-ai' && request.method === 'GET') {
      return runEdgeAiDiagnostic(env, requestId);
    }

    if (url.pathname.startsWith('/api/')) {
      const origin = env.BITEY_BACKEND_ORIGIN;
      if (!origin) {
        return jsonError('Bitey backend origin is not configured', 500, requestId);
      }

      const upstreamUrl = new URL(url.pathname + url.search, origin);
      const headers = new Headers(request.headers);
      headers.set('x-bitey-channel', 'web');
      headers.set('x-bitey-origin', 'cloudflare');
      headers.set('x-forwarded-host', url.host);
      headers.set('x-request-id', requestId);
      headers.delete('host');

      const canUseAiFallback = request.method === 'POST' && url.pathname.includes('/conversations/') && url.pathname.endsWith('/messages');
      const requestClone = canUseAiFallback ? request.clone() : null;

      try {
        const upstream = await fetch(upstreamUrl, {
          method: request.method,
          headers,
          body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
          redirect: 'follow'
        });

        if (canUseAiFallback && env.AI) {
          const fallback = await tryRealAiFallback(upstream, requestClone, env, requestId);
          if (fallback) return fallback;
        }

        const responseHeaders = new Headers(upstream.headers);
        responseHeaders.set('Cache-Control', 'no-store');
        responseHeaders.set('X-Bitey-Edge', 'cloudflare');
        responseHeaders.set('X-Bitey-Request-Id', requestId);

        return new Response(upstream.body, {
          status: upstream.status,
          statusText: upstream.statusText,
          headers: responseHeaders
        });
      } catch (error) {
        console.error('Bitey upstream proxy error', { requestId, path: url.pathname, error: String(error) });
        if (canUseAiFallback && env.AI && requestClone) {
          const fallback = await runRealAiFallback(requestClone, env, requestId, error);
          if (fallback) return fallback;
        }
        return jsonError('Bitey backend is temporarily unavailable', 502, requestId);
      }
    }

    return env.ASSETS.fetch(request);
  }
};

async function runEdgeAiDiagnostic(env, requestId) {
  if (!env.AI) return jsonError('Workers AI binding is unavailable', 503, requestId);
  try {
    const response = await env.AI.run(AI_MODEL, {
      messages: [
        { role: 'system', content: 'Responde únicamente con el resultado de la operación solicitada.' },
        { role: 'user', content: '¿Cuánto es 2+2?' }
      ],
      max_tokens: 32,
      temperature: 0
    });
    const answer = String(response?.response || response?.result || '').trim();
    if (!answer) return jsonError('Workers AI returned an empty response', 502, requestId);
    return new Response(JSON.stringify({
      ok: true,
      selected_provider: 'cloudflare-workers-ai',
      model: AI_MODEL,
      answer,
      request_id: requestId
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Bitey-Edge': 'cloudflare-ai-diagnostic', 'X-Bitey-Request-Id': requestId }
    });
  } catch (error) {
    console.error('Bitey Workers AI diagnostic failed', { requestId, error: String(error) });
    return jsonError('Workers AI model execution failed', 502, requestId);
  }
}

async function tryRealAiFallback(upstream, request, env, requestId) {
  if (upstream.ok) {
    try {
      const body = await upstream.clone().json();
      const answer = String(body?.answer || '');
      if (answer !== NO_PROVIDER_ANSWER && answer !== LEGACY_NO_PROVIDER_ANSWER) return null;
    } catch (_) {
      return null;
    }
  }
  return runRealAiFallback(request, env, requestId, new Error(`backend_status_${upstream.status}`));
}

async function runRealAiFallback(request, env, requestId, cause) {
  try {
    const payload = await request.json();
    const message = String(payload?.message || '').trim();
    const conversationId = String(request.url).match(/conversations\/([^/]+)\/messages/)?.[1] || '';
    if (!message) return null;

    const response = await env.AI.run(AI_MODEL, {
      messages: [
        {
          role: 'system',
          content: 'Eres Bitey IA, una inteligencia general. Responde en el idioma del usuario. Sé útil, clara y honesta. No inventes datos. Si la consulta requiere información actual, indica que debe investigarse con fuentes antes de afirmar hechos actuales.'
        },
        { role: 'user', content: message }
      ],
      max_tokens: 900,
      temperature: 0.2
    });

    const answer = String(response?.response || response?.result || '').trim();
    if (!answer) return null;

    return new Response(JSON.stringify({
      conversation_id: conversationId,
      answer,
      research_required: false,
      research_reasons: [],
      providers: [AI_MODEL],
      selected_provider: 'cloudflare-workers-ai',
      elapsed_ms: null,
      activity_events: ['Generación realizada por un modelo de lenguaje real de Cloudflare Workers AI.'],
      request_id: requestId
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-Bitey-Edge': 'cloudflare-ai-fallback',
        'X-Bitey-Request-Id': requestId
      }
    });
  } catch (error) {
    console.error('Bitey Workers AI fallback failed', { requestId, cause: String(cause), error: String(error) });
    return null;
  }
}

function jsonError(message, status, requestId) {
  return new Response(JSON.stringify({ error: message, request_id: requestId }), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Bitey-Edge': 'cloudflare',
      'X-Bitey-Request-Id': requestId
    }
  });
}
