export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith('/api/')) {
      const origin = env.BITEY_API_ORIGIN;
      if (!origin) {
        return new Response(JSON.stringify({ error: 'Bitey API origin is not configured' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
        });
      }

      const upstreamUrl = new URL(url.pathname + url.search, origin);
      const headers = new Headers(request.headers);
      headers.set('x-bitey-channel', 'web');
      headers.set('x-bitey-origin', 'cloudflare');
      headers.set('x-forwarded-host', url.host);

      const upstream = await fetch(upstreamUrl, {
        method: request.method,
        headers,
        body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
        redirect: 'follow'
      });

      const responseHeaders = new Headers(upstream.headers);
      responseHeaders.set('Cache-Control', 'no-store');
      responseHeaders.set('X-Bitey-Edge', 'cloudflare');

      return new Response(upstream.body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers: responseHeaders
      });
    }

    return env.ASSETS.fetch(request);
  }
};
