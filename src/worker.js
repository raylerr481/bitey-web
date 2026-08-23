const SUPRABRAIN_ORIGIN = 'https://bitey-ia-suprabrain.onrender.com';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith('/api/')) {
      const upstreamUrl = new URL(url.pathname + url.search, SUPRABRAIN_ORIGIN);
      const headers = new Headers(request.headers);
      headers.set('x-bitey-channel', 'web');
      headers.set('x-bitey-origin', 'cloudflare');

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
