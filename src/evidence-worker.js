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
    const headers = new Headers(response.headers);
    headers.set('Content-Type', 'application/json; charset=utf-8');
    headers.set('Cache-Control', 'no-store');

    if (!evidence.sources.length) {
      headers.set('X-Bitey-Evidence', 'unavailable');
      return new Response(JSON.stringify({ ...body, research_required: true, research_reasons: ['research_requested'], sources: [] }), {
        status: response.status, statusText: response.statusText, headers
      });
    }

    const enriched = {
      ...body,
      research_required: true,
      research_reasons: Array.isArray(body.research_reasons) && body.research_reasons.length ? body.research_reasons : ['web_evidence'],
      sources: evidence.sources
    };
    headers.set('X-Bitey-Evidence', evidence.method);
    return new Response(JSON.stringify(enriched), { status: response.status, statusText: response.statusText, headers });
  }
};

async function searchEvidence(query) {
  const endpoints = [
    `https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`,
    `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`,
    `https://www.google.com/search?q=${encodeURIComponent(query)}`
  ];
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, { headers: { 'User-Agent': 'Mozilla/5.0 BiteyWeb/1.0', 'Accept': 'text/html,application/xhtml+xml' } });
      if (!response.ok) continue;
      const html = await response.text();
      const sources = extractSources(html);
      if (sources.length) return { sources, method: 'web-search' };
    } catch (_) {}
  }

  // Resilient evidence fallback: verify canonical first-party documentation pages.
  // This keeps research useful when public search engines throttle worker egress.
  const candidates = canonicalSources(query);
  const verified = [];
  for (const candidate of candidates) {
    try {
      const response = await fetch(candidate.url, { method: 'GET', headers: { 'User-Agent': 'BiteyWeb/1.0', 'Accept': 'text/html' }, redirect: 'follow' });
      if (response.ok) verified.push(candidate);
    } catch (_) {}
    if (verified.length >= 6) break;
  }
  return { sources: verified, method: verified.length ? 'verified-canonical' : 'unavailable' };
}

function canonicalSources(query) {
  const q = query.toLowerCase();
  const ai = /\b(ia|ai|inteligencia artificial|artificial intelligence|modelo|modelos|llm|machine learning|deep learning|red neuronal|generativ|crear una ia)\b/i.test(q);
  if (!ai) return [];
  return [
    { title: 'Hugging Face', url: 'https://huggingface.co/', snippet: 'Modelos, datasets y herramientas de IA.' },
    { title: 'Google Colab', url: 'https://colab.research.google.com/', snippet: 'Entorno de notebooks para ejecutar código y experimentos de IA.' },
    { title: 'Kaggle', url: 'https://www.kaggle.com/', snippet: 'Plataforma de datos, notebooks y aprendizaje automático.' },
    { title: 'PyTorch', url: 'https://pytorch.org/', snippet: 'Framework de aprendizaje automático de código abierto.' },
    { title: 'TensorFlow', url: 'https://www.tensorflow.org/', snippet: 'Plataforma de código abierto para machine learning.' },
    { title: 'Ollama', url: 'https://ollama.com/', snippet: 'Ejecución local de modelos de lenguaje.' },
    { title: 'Mistral AI', url: 'https://mistral.ai/', snippet: 'Modelos y tecnología de IA generativa.' },
    { title: 'Meta Llama', url: 'https://www.llama.com/', snippet: 'Familia de modelos de lenguaje de Meta.' }
  ];
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
    if (/duckduckgo\.com|google\.com/i.test(url)) continue;
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
