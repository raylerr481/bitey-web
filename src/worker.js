export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const requestId = request.headers.get('x-request-id') || crypto.randomUUID();

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

      try {
        const upstream = await fetch(upstreamUrl, {
          method: request.method,
          headers,
          body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
          redirect: 'follow'
        });

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
        return jsonError('Bitey backend is temporarily unavailable', 502, requestId);
      }
    }

    return env.ASSETS.fetch(request);
  }
};

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
