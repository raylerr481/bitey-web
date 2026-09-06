import biteyWorker from './worker.js';

const RESEARCH_RE = /\b(busca|buscar|búsqueda|investiga|investigar|investigación|fuentes|compara|comparar|comparativa|comparativas|contrasta|alternativas|opciones|mejores|recomendaciones|recomienda|gratuita|gratuito|gratuitas|gratuitos|search|research|latest|actual|hoy|noticias|news|precio|precios|quién|quien|what|who|where|when|how much)\b/i;

export default {
  async fetch(request, env, ctx) {
    const response = await biteyWorker.fetch(request, env, ctx);
    if (request.method !== 'POST' || !new URL(request.url).pathname.includes('/conversations/') || !new URL(request.url).pathname.endsWith('/messages')) {
      return response;
    }

    let payload;
    try { payload = await request.clone().json(); } catch (_) { return response; }
    const message = String(payload?.message || '').trim();
    if (!RESEARCH_RE.test(message) || !response.ok) return response;

    let body;
    try { body = await response.clone().json(); } catch (_) { return response; }
    if (!body?.answer) return response;
    if (Array.isArray(body.sources) && body.sources.length > 0) return response;

    const evidence = await searchEvidence(message);
    if (!evidence.sources.length) {
      const headers = new Headers(response.headers);
      headers.set('X-Bitey-Evidence', 'unavailable');
      return new Response(JSON.stringify({ ...body, research_required: true, research_reasons: ['research_requested'] }), {
        status: response.status, statusText: response.statusText, headers
      });
    }

    const enriched = {
      ...body,
      research_required: true,
      research_reasons: Array.isArray(body.research_reasons) && body.research_reasons.length ? body.research_reasons : ['web_evidence'],
      sources: evidence.sources
    };
    const headers = new Headers(response.headers);
    headers.set('Content-Type', 'application/json; charset=utf-8');
    headers.set('Cache-Control', 'no-store');
    headers.set('X-Bitey-Evidence', 'duckduckgo-lite');
    return new Response(JSON.stringify(enriched), { status: response.status, statusText: response.statusText, headers });
  }
};

async function searchEvidence(query) {
  const endpoints = [
    `https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`,
    `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`
  ];
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, { headers: { 'User-Agent': 'BiteyWeb/1.0', 'Accept': 'text/html' } });
      if (!response.ok) continue;
      const html = await response.text();
      const sources = extractSources(html);
      if (sources.length) return { sources };
    } catch (_) {}
  }
  return { sources: [] };
}

function extractSources(html) {
  const sources = [];
  const seen = new Set();
  const anchorRe = /<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  let match;
  while ((match = anchorRe.exec(html)) && sources.length < 8) {
    let url = decodeHtml(match[1]);
    const title = cleanText(match[2]);
    const redirect = url.match(/[?&](?:uddg|rut)=([^&]+)/i);
    if (redirect) {
      try { url = decodeURIComponent(redirect[1]); } catch (_) {}
    }
    if (!/^https?:\/\//i.test(url)) continue;
    if (/duckduckgo\.com/i.test(url)) continue;
    if (!title || title.length < 3 || seen.has(url)) continue;
    seen.add(url);
    sources.push({ title, url, snippet: '' });
  }
  return sources;
}

function cleanText(value) {
  return decodeHtml(String(value || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim());
}

function decodeHtml(value) {
  return String(value || '')
    .replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>');
}
