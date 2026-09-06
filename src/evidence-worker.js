import biteyWorker from './worker.js';

const RESEARCH_RE = /\b(busca|buscar|búsqueda|investiga|investigar|investigación|fuentes|compara|comparar|comparativa|comparativas|contrasta|alternativas|opciones|mejores|recomendaciones|recomienda|gratuita|gratuito|gratuitas|gratuitos|search|research|latest|actual|hoy|noticias|news|precio|precios|quién|quien|what|who|where|when|how much)\b/i;

export default {
  async fetch(request, env, ctx) {
    const response = await biteyWorker.fetch(request, env, ctx);
    const url = new URL(request.url);
    if (request.method !== 'POST' || !url.pathname.includes('/conversations/') || !url.pathname.endsWith('/messages')) return response;
    let payload;
    try { payload = await request.clone().json(); } catch (_) { return response; }
    const message = String(payload?.message || '').trim();
    if (!RESEARCH_RE.test(message) || !response.ok) return response;
    let body;
    try { body = await response.clone().json(); } catch (_) { return response; }
    if (!body?.answer || (Array.isArray(body.sources) && body.sources.length > 0)) return response;
    const evidence = await searchEvidence(message);
    const headers = new Headers(response.headers);
    headers.set('Content-Type', 'application/json; charset=utf-8');
    headers.set('Cache-Control', 'no-store');
    if (!evidence.sources.length) {
      headers.set('X-Bitey-Evidence', 'unavailable-free-only');
      return new Response(JSON.stringify({ ...body, research_required: true, research_reasons: ['research_requested'], sources: [] }), { status: response.status, statusText: response.statusText, headers });
    }
    headers.set('X-Bitey-Evidence', evidence.method);
    return new Response(JSON.stringify({ ...body, research_required: true, research_reasons: Array.isArray(body.research_reasons) && body.research_reasons.length ? body.research_reasons : ['web_evidence'], sources: evidence.sources }), { status: response.status, statusText: response.statusText, headers });
  }
};

const BROWSER_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'es-ES,es;q=0.9,en;q=0.7',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'none',
  'Sec-Fetch-Dest': 'document'
};

async function searchEvidence(query) {
  // ZERO_COST_BY_DEFAULT: only free/public search endpoints are allowed here.
  // Never silently fall back to a potentially billable search API.
  const endpoints = [
    `https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`,
    `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`
  ];
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, { headers: BROWSER_HEADERS });
      if (!response.ok) continue;
      const html = await response.text();
      const sources = extractSources(html);
      if (sources.length) return { sources, method: 'duckduckgo-free-search' };
    } catch (_) {}
  }
  const verified = await verifyCanonicalSources(query);
  return { sources: verified, method: verified.length ? 'verified-canonical-free' : 'unavailable' };
}

async function verifyCanonicalSources(query) {
  const candidates = canonicalSources(query); const verified = [];
  for (const candidate of candidates) {
    try {
      const response = await fetch(candidate.url, { headers: BROWSER_HEADERS, redirect: 'follow' });
      if (response.ok) verified.push({ ...candidate, verified: true });
    } catch (_) {}
    if (verified.length >= 6) break;
  }
  return verified;
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
  const sources = []; const seen = new Set();
  const anchorRe = /<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  let match;
  while ((match = anchorRe.exec(html)) && sources.length < 8) {
    let url = decodeHtml(match[1]); const title = cleanText(match[2]);
    const redirect = url.match(/[?&](?:uddg|rut)=([^&]+)/i); if (redirect) { try { url = decodeURIComponent(redirect[1]); } catch (_) {} }
    if (!/^https?:\/\//i.test(url) || /duckduckgo\.com/i.test(url) || !title || title.length < 3 || seen.has(url)) continue;
    seen.add(url); sources.push({ title, url, snippet: '' });
  }
  return sources;
}
function cleanText(value) { return decodeHtml(String(value || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()); }
function decodeHtml(value) { return String(value || '').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>'); }
