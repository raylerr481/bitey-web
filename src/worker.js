import { classifyCapability } from './capability-router.js';
import { filterConversationHistory } from './conversation-isolation.js';

const AI_MODEL = '@cf/google/gemma-4-26b-a4b-it';
const NO_PROVIDER_ANSWER = 'Ahora mismo no puedo completar esta consulta. Inténtalo nuevamente en unos momentos.';
const LEGACY_NO_PROVIDER_ANSWER = 'No pude obtener una respuesta de Bitey IA en este momento. Inténtalo nuevamente en unos momentos.';
const WEATHER_RE = /\b(temperatura|clima|tiempo|weather|temperature|forecast|previs[aã]o)\b/i;
const RESEARCH_RE = /\b(busca|buscar|búsqueda|investiga|investigar|investigación|fuentes|compara|comparar|comparativa|comparativas|contrasta|alternativas|opciones|mejores|recomendaciones|recomienda|gratuita|gratuito|gratuitas|gratuitos|search|research|latest|actual|hoy|noticias|news|precio|precios|quién|quien|what|who|where|when|how much)\b/i;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const requestId = request.headers.get('x-request-id') || crypto.randomUUID();
    if (url.pathname === '/api/diagnostics/edge-ai' && request.method === 'GET') return runEdgeAiDiagnostic(env, requestId);
    if (url.pathname.startsWith('/api/')) {
      const origin = env.BITEY_BACKEND_ORIGIN;
      if (!origin) return jsonError('Bitey backend origin is not configured', 500, requestId);
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
        const upstream = await fetch(upstreamUrl, { method: request.method, headers, body: ['GET','HEAD'].includes(request.method) ? undefined : request.body, redirect: 'follow' });
        if (canUseAiFallback && env.AI) {
          const fallback = await tryRealAiFallback(upstream, requestClone, env, requestId, origin);
          if (fallback) return fallback;
        }
        const responseHeaders = new Headers(upstream.headers);
        responseHeaders.set('Cache-Control', 'no-store');
        responseHeaders.set('X-Bitey-Edge', 'cloudflare');
        responseHeaders.set('X-Bitey-Request-Id', requestId);
        return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers: responseHeaders });
      } catch (error) {
        console.error('Bitey upstream proxy error', { requestId, path: url.pathname, error: String(error) });
        if (canUseAiFallback && env.AI && requestClone) {
          const fallback = await runRealAiFallback(requestClone, env, requestId, error, origin);
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
      temperature: 0,
      chat_template_kwargs: { enable_thinking: false }
    });
    const answer = extractAiText(response);
    if (!answer) {
      console.error('Workers AI diagnostic returned no text', { requestId, response: safeAiShape(response) });
      return jsonError('Workers AI returned an empty response', 502, requestId);
    }
    return jsonResponse({ ok: true, selected_provider: 'cloudflare-workers-ai', model: AI_MODEL, answer, request_id: requestId }, 200, 'cloudflare-ai-diagnostic', requestId);
  } catch (error) {
    console.error('Bitey Workers AI diagnostic failed', { requestId, error: String(error) });
    return jsonError('Workers AI model execution failed', 502, requestId);
  }
}

async function tryRealAiFallback(upstream, request, env, requestId, origin) {
  if (!request) return null;
  let degraded = !upstream.ok;
  let upstreamBody = null;
  try {
    const raw = await upstream.clone().text();
    try { upstreamBody = JSON.parse(raw); } catch (_) {}
    const answer = String(upstreamBody?.answer || '').trim();
    const providers = Array.isArray(upstreamBody?.providers) ? upstreamBody.providers : [];
    degraded = degraded || !answer || !providers.length || answer === NO_PROVIDER_ANSWER || answer === LEGACY_NO_PROVIDER_ANSWER || answer.includes(NO_PROVIDER_ANSWER) || answer.includes(LEGACY_NO_PROVIDER_ANSWER) || answer.startsWith('Ahora mismo no puedo completar esta consulta') || answer.startsWith('No pude obtener una respuesta de Bitey IA');
    if (!degraded) return await enrichSuccessfulResponse(upstream, request, requestId);
  } catch (_) {
    degraded = true;
  }
  return runRealAiFallback(request, env, requestId, new Error(`backend_status_${upstream.status}`), origin, upstreamBody);
}

async function enrichSuccessfulResponse(upstream, request, requestId) {
  if (!request || !upstream.ok) return null;
  let payload;
  try {
    payload = await request.clone().json();
  } catch (_) {
    return null;
  }
  const message = String(payload?.message || '').trim();
  if (!message || (!WEATHER_RE.test(message) && !RESEARCH_RE.test(message))) return null;
  const evidence = await recoverToolEvidence(message, requestId);
  const sources = Array.isArray(evidence?.sources) ? evidence.sources : [];
  if (!sources.length) return null;
  let body;
  try {
    body = JSON.parse(await upstream.clone().text());
  } catch (_) {
    return null;
  }
  if (Array.isArray(body?.sources) && body.sources.length) return null;
  body.sources = sources;
  if (RESEARCH_RE.test(message)) {
    body.research_required = true;
    if (!Array.isArray(body.research_reasons) || !body.research_reasons.length) body.research_reasons = ['evidence_recovery'];
  }
  const headers = new Headers(upstream.headers);
  headers.set('Content-Type', 'application/json; charset=utf-8');
  headers.set('Cache-Control', 'no-store');
  headers.set('X-Bitey-Edge', 'cloudflare-ai-evidence-enrichment');
  headers.set('X-Bitey-Request-Id', requestId);
  return new Response(JSON.stringify(body), { status: upstream.status, statusText: upstream.statusText, headers });
}

async function runRealAiFallback(request, env, requestId, cause, origin, upstreamBody = null) {
  if (!env.AI) return null;
  let payload;
  try {
    payload = await request.clone().json();
  } catch (error) {
    console.error('Bitey edge fallback could not parse request', { requestId, error: String(error) });
    return null;
  }
  const message = String(payload?.message || '').trim();
  const conversationId = String(request.url).match(/conversations\/([^/]+)\/messages/)?.[1] || '';
  if (!message) return null;

  const capability = resolveFallbackCapability(payload, message);
  if (capability !== 'general') {
    console.warn('Bitey edge fallback blocked for specialized capability', { requestId, capability });
    return specializedFallbackBlocked(capability, requestId);
  }

  let history = [];
  if (conversationId) history = await loadConversationHistory(origin, conversationId, requestId);
  const isolatedHistory = filterConversationHistory(history, capability);
  const compactHistory = isolatedHistory.slice(-8).map(item => ({ role: item.role, content: String(item.content || '').slice(-800) })).filter(item => item.content && (item.role === 'user' || item.role === 'assistant'));

  const evidence = await recoverToolEvidence(message, requestId);
  const backendEvidenceCapability = String(upstreamBody?.capability || upstreamBody?.routing || upstreamBody?.['x-bitey-capability'] || '').trim();
  const backendEvidence = backendEvidenceCapability && backendEvidenceCapability !== 'general' ? '' : String(upstreamBody?.evidence_context || '').trim();
  const combinedEvidence = [backendEvidence, evidence?.text || ''].filter(Boolean).join('\n\n').slice(0, 10000);
  const backendSources = backendEvidenceCapability && backendEvidenceCapability !== 'general' ? [] : (Array.isArray(upstreamBody?.sources) ? upstreamBody.sources : []);
  const sources = backendSources.length ? backendSources : (Array.isArray(evidence?.sources) ? evidence.sources : []);
  const evidenceInstruction = combinedEvidence
    ? `EVIDENCIA RECUPERADA POR BITEY:\n${combinedEvidence}\n\nUsa esta evidencia para responder. No inventes datos y no menciones herramientas internas.`
    : (RESEARCH_RE.test(message) ? 'La consulta puede requerir información externa. Si no hay evidencia recuperada, no inventes datos; explica brevemente la limitación.' : '');
  const sourceInstruction = sources.length
    ? `FUENTES CONSULTADAS:\n${sources.map((s, i) => `[${i + 1}] ${s.title || s.url || 'Fuente'} — ${s.url || ''}`).join('\n')}\n\nCuando afirmes datos procedentes de estas fuentes, cita [1], [2], etc. No inventes referencias.`
    : '';
  const system = 'Eres Bitey IA, una inteligencia general. Responde en el idioma del usuario. Sé útil, clara y directa. No inventes datos. Mantén continuidad con el historial disponible. No expongas diagnósticos internos, nombres de capas cognitivas, contratos, errores de proveedores ni mensajes de recuperación.';
  const messages = [{ role: 'system', content: system }, ...(evidenceInstruction ? [{ role: 'system', content: evidenceInstruction }] : []), ...(sourceInstruction ? [{ role: 'system', content: sourceInstruction }] : []), ...compactHistory, { role: 'user', content: message }];

  const attempts = [
    { messages, max_tokens: 512 },
    { messages: [{ role: 'system', content: system }, ...(evidenceInstruction ? [{ role: 'system', content: evidenceInstruction }] : []), ...(sourceInstruction ? [{ role: 'system', content: sourceInstruction }] : []), { role: 'user', content: message }], max_tokens: 512 }
  ];
  for (let index = 0; index < attempts.length; index++) {
    try {
      const response = await env.AI.run(AI_MODEL, { messages: attempts[index].messages, max_tokens: attempts[index].max_tokens, temperature: 0.2, chat_template_kwargs: { enable_thinking: false } });
      const answer = extractAiText(response);
      if (!answer) throw new Error('empty_response');
      return jsonResponse({ conversation_id: conversationId, answer, research_required: Boolean(combinedEvidence), research_reasons: combinedEvidence ? ['evidence_recovery'] : [], providers: [AI_MODEL], selected_provider: 'cloudflare-workers-ai', elapsed_ms: null, activity_events: [combinedEvidence ? 'Respuesta final generada por un modelo de lenguaje real usando evidencia recuperada por Bitey.' : 'Generación de recuperación realizada por un modelo de lenguaje real de Cloudflare Workers AI.'], sources, request_id: requestId }, 200, 'cloudflare-ai-fallback', requestId);
    } catch (error) {
      console.error('Bitey Workers AI fallback attempt failed', { requestId, attempt: index + 1, cause: String(cause), error: String(error) });
    }
  }
  return null;
}

function resolveFallbackCapability(payload, message) {
  const explicit = String(payload?.capability || payload?.routing || payload?.['x-bitey-capability'] || '').toLowerCase();
  if (explicit === 'enterprise' || explicit === 'jobia' || explicit === 'sbt' || explicit === 'general') return explicit;
  return classifyCapability(message).capability || 'general';
}

function specializedFallbackBlocked(capability, requestId) {
  const answer = capability === 'sbt'
    ? 'La capacidad de SBT no está disponible en este momento. No voy a simular una respuesta de trading o inversión.'
    : capability === 'enterprise'
      ? 'La capacidad de Bitey Enterprise no está disponible en este momento. No voy a simular una respuesta especializada de marketing o crecimiento empresarial.'
      : 'La capacidad de JobIA no está disponible en este momento. No voy a simular una respuesta especializada de empleo.';
  return jsonResponse({ answer, providers: [], selected_provider: null, specialized_unavailable: true, capability, request_id: requestId }, 503, 'specialized-fallback-blocked', requestId);
}

function resolveFallbackCapabilityLegacy(payload, message) {
  const explicit = payload?.capability || payload?.routing || payload?.['x-bitey-capability'];
  if (explicit === 'jobia' || explicit === 'sbt' || explicit === 'general') return explicit;
  return classifyCapability(message).capability || 'general';
}

async function recoverToolEvidence(message, requestId) {
  try {
    if (WEATHER_RE.test(message)) return await recoverWeather(message, requestId);
    if (RESEARCH_RE.test(message)) return await recoverSearch(message, requestId);
  } catch (error) {
    console.warn('Bitey edge evidence recovery failed', { requestId, error: String(error) });
  }
  return null;
}

function weatherLocation(message) {
  const known = message.match(/\b(esteio|porto alegre)\b/i);
  if (known) return known[1];
  const match = message.match(/(?:en|in|em|de|da|do)\s+(.+?)(?:,\s*(?:brasil|brazil))?(?:[?!.]|$)/i);
  return (match?.[1] || '').replace(/\b(?:rio grande do sul|rs|estado de)\b/ig, '').replace(/\s+/g, ' ').trim() || null;
}

async function recoverWeather(message, requestId) {
  const locationQuery = weatherLocation(message);
  if (!locationQuery) return null;
  const geoUrl = new URL('https://geocoding-api.open-meteo.com/v1/search');
  geoUrl.searchParams.set('name', locationQuery); geoUrl.searchParams.set('count', '5'); geoUrl.searchParams.set('language', 'pt'); geoUrl.searchParams.set('format', 'json');
  const geoResponse = await fetch(geoUrl, { headers: { 'User-Agent': 'BiteyWeb/1.0' } });
  if (!geoResponse.ok) return null;
  const locations = (await geoResponse.json())?.results || [];
  if (!locations.length) return null;
  const location = locations.find(x => String(x?.name || '').toLowerCase() === locationQuery.toLowerCase()) || locations[0];