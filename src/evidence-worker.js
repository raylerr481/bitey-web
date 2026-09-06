import biteyWorker from './worker.js';

const RESEARCH_RE = /\b(busca|buscar|búsqueda|investiga|investigar|investigación|fuentes|compara|comparar|comparativa|comparativas|contrasta|alternativas|opciones|mejores|recomendaciones|recomienda|gratuita|gratuito|gratuitas|gratuitos|search|research|latest|actual|hoy|noticias|news|precio|precios|quién|quien|what|who|where|when|how much)\b/i;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method !== 'POST' || !url.pathname.includes('/conversations/') || !url.pathname.endsWith('/messages')) {
      return biteyWorker.fetch(request, env, ctx);
    }
    let payload;
    try { payload = await request.clone().json(); } catch (_) { return biteyWorker.fetch(request, env, ctx); }
    const message = String(payload?.message || '').trim();
    const researchRequested = RESEARCH_RE.test(message);
    const response = await biteyWorker.fetch(request, env, ctx);
    if (!researchRequested || !response.ok) return response;
    let body;
    try { body = await response.clone().json(); } catch (_) { return response; }
    if (!body?.answer) return response;
    // The edge owns this contract: explicit research requests must be marked as research.
    if (Array.isArray(body.sources) && body.sources.length > 0) {
      return withResearchContract(response, body, body.sources, 'backend-evidence');
    }
    const evidence = await searchEvidence(message);
    const sources = Array.isArray(evidence?.sources) ? evidence.sources : [];
    return withResearchContract(response, body, sources, evidence?.method || 'unavailable-free-only');
  }
};

function withResearchContract(response, body, sources, method) {
  const headers = new Headers(response.headers);
  headers.set('Content-Type', 'application/json; charset=utf-8');
  headers.set('Cache-Control', 'no-store');
  headers.set('X-Bitey-Research', 'required');
  headers.set('X-Bitey-Evidence', method);
  return new Response(JSON.stringify({
    ...body,
    research_required: true,
    research_reasons: Array.isArray(body.research_reasons) && body.research_reasons.length ? body.research_reasons : ['research_requested'],
    sources
  }), { status: response.status, statusText: response.statusText, headers });
}

const BROWSER_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'es-ES,es;q=0.9,en;q=0.7',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'none',
  'Sec-Fetch-Dest': 'document'
};

async function searchEvidence(query) {
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
  const wiki = await wikipediaSources(query);
  if (wiki.length) return { sources: wiki, method: 'wikipedia-free-search' };
  const verified = await verifyCanonicalSources(query);
  return { sources: verified, method: verified.length ? 'verified-canonical-free' : 'unavailable-free-only' };
}

async function wikipediaSources(query) {
  try {
    const url = `https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(query)}&srlimit=6&format=json&origin=*`;
    const response = await fetch(url, { headers: { ...BROWSER_HEADERS, 'Accept': 'application/json' } });
    if (!response.ok) return [];
    const data = await response.json();
    const pages = Array.isArray(data?.query?.search) ? data.query.search : [];
    return pages.slice(0, 6).map((page) => ({
      title: cleanText(page?.title),
      url: `https://es.wikipedia.org/wiki/${encodeURIComponent(String(page?.title || '').replace(/ /g, '_'))}`,
      snippet: cleanText(page?.snippet),
      verified: true
    })).filter((source) => source.title && source.url);
  } catch (_) { return []; }
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
