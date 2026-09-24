const DICTIONARY = new Map([
  ['q','que'], ['k','que'], ['pq','porque'], ['xq','porque'],
  ['tb','tambien'], ['tmb','tambien'], ['dnd','donde'], ['qdo','cuando'],
  ['cm','como'], ['ola','hola'], ['holaa','hola'],
  ['timepoe','tiempo'], ['tiempoe','tiempo'], ['tiempe','tiempo'],
  ['qhora','que hora'],
  ['temp','temperatura'], ['tempertaura','temperatura'], ['temperatua','temperatura'],
  ['cliam','clima'], ['clm','clima'], ['previsao','previsao'], ['previsaoo','previsao'],
  ['wheather','weather'], ['weater','weather'], ['teh','the'],
  ['mercdo','mercado'], ['mercaod','mercado'], ['cotizacoin','cotizacion'],
  ['infomacion','informacion'], ['informcaion','informacion'],
  ['tecnologia','tecnologia'], ['inteligenciaartificial','inteligencia artificial']
]);


const DOMAIN_LEXICON = {
  time: ['hora','horario','hora actual','time','current time'],
  weather: ['temperatura','clima','tiempo','tempo','weather','temperature','forecast','previsao','previsão','chuva','lluvia','rain','sol','nublado','ensolarado'],
  finance: ['mercado','trading','bitcoin','acciones','bolsa','cotizacion','cotação','preço','precio','dividendos','stocks','forex','euro','dolar','dólar'],
  jobs: ['empleo','trabajo','vacante','curriculum','currículo','cv','entrevista','salario','sueldo','emprego','trabalho','vaga'],
  code: ['codigo','código','programacion','programação','javascript','python','html','css','api','bug','error','docker','linux','wordpress'],
  business: ['cliente','clientes','ticket','tickets','soporte','suporte','empresa','empresarial','crm','saas','marketing','whatsapp']
};

const SEMANTIC_TERMS = [
  'temperatura','clima','tiempo','tempo','weather','temperature','forecast','previsao',
  'mercado','trading','bitcoin','acciones','bolsa','empleo','trabajo','vacante',
  'curriculum','codigo','programacion','wordpress','linux','windows','docker'
];

const LANGUAGE_MARKERS = {
  esDistinctive: /\b(una|uno|unos|unas|donde|cuando|quien|porque|para|tambien|hace|est[aá]s|est[aá]|puede|quiero|dime|sobre|desde|hasta)\b|[ñ¿¡]/i,
  ptDistinctive: /\b(uma|um|uns|umas|onde|quando|quem|porque|também|onde|voc[eê]|est[aá]|pode|quero|diga|sobre|desde|at[eé]|não|sim|previs[aã]o)\b|[ãõç]/i,
  enDistinctive: /\b(what|how|where|when|who|why|the|are|with|this|that|from|today|can|want|please|weather|temperature)\b/i,
  es: /\b(que|qué|como|cómo|donde|dónde|cuando|cuándo|quien|quién|para|con|por|una|una|el|la|los|las|es|en|hace|tiempo|clima)\b/i,
  pt: /\b(que|como|onde|quando|quem|para|com|por|uma|o|a|os|as|é|em|tempo|clima|previsao)\b/i,
  en: /\b(what|how|where|when|who|why|the|is|are|for|with|weather|temperature)\b/i
};

export function analyzeLanguage(message = '') {
  const original = String(message || '').trim();
  if (!original) return { original, normalized: '', language: 'unknown', corrections: [], confidence: 1 };

  const tokens = original.split(/(\s+)/);
  const corrections = [];
  const normalizedTokens = tokens.map(part => {
    if (/^\s+$/.test(part) || !part) return part;
    const leading = (part.match(/^[^\p{L}\p{N}]*/u) || [''])[0];
    const trailing = (part.match(/[^\p{L}\p{N}]*$/u) || [''])[0];
    const core = part.slice(leading.length, part.length - trailing.length || undefined);
    const key = core.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    if (!key) return part;
    if (DICTIONARY.has(key)) {
      const replacement = DICTIONARY.get(key);
      corrections.push({ from: core, to: replacement, method: 'dictionary' });
      return leading + replacement + trailing;
    }
    const fuzzy = fuzzyCorrection(key);
    if (fuzzy) {
      corrections.push({ from: core, to: fuzzy, method: 'contextual_fuzzy' });
      return leading + fuzzy + trailing;
    }
    return part;
  });

  const normalized = normalizedTokens.join('').replace(/\s+/g, ' ').trim();
  const language = detectLanguage(normalized);
  const intent = detectIntent(normalized);
  const domains = detectDomains(normalized);
  const entities = extractEntities(normalized);
  const confidence = corrections.length ? Math.min(0.99, 0.86 + Math.min(corrections.length, 4) * 0.03) : 0.98;

  return { original, normalized, language, intent, domains, entities, corrections, confidence };
}

function fuzzyCorrection(token) {
  if (token.length < 4 || token.length > 18) return null;
  let best = null;
  let bestDistance = Infinity;
  for (const candidate of SEMANTIC_TERMS) {
    if (Math.abs(candidate.length - token.length) > 3) continue;
    const distance = levenshtein(token, candidate);
    const limit = token.length <= 6 ? 1 : token.length <= 10 ? 2 : 3;
    if (distance <= limit && distance < bestDistance) {
      best = candidate;
      bestDistance = distance;
    }
  }
  return best;
}

function levenshtein(a, b) {
  const prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let current = [i];
    for (let j = 1; j <= b.length; j++) {
      current[j] = Math.min(
        current[j - 1] + 1,
        prev[j] + 1,
        prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)
      );
    }
    for (let j = 0; j <= b.length; j++) prev[j] = current[j];
  }
  return prev[b.length];
}

function detectLanguage(text) {
  const value = String(text || '');
  const base = Object.fromEntries(Object.entries(LANGUAGE_MARKERS).filter(([key]) => ['es','pt','en'].includes(key)).map(([language, pattern]) => [
    language, (value.match(new RegExp(pattern.source, 'gi')) || []).length
  ]));
  const distinctive = {
    es: LANGUAGE_MARKERS.esDistinctive.test(value) ? 3 : 0,
    pt: LANGUAGE_MARKERS.ptDistinctive.test(value) ? 3 : 0,
    en: LANGUAGE_MARKERS.enDistinctive.test(value) ? 3 : 0
  };
  const scores = Object.keys(base).map(language => [language, base[language] + distinctive[language]])
    .sort((a, b) => b[1] - a[1]);
  if (!scores.length || scores[0][1] === 0) return 'unknown';
  if (scores.length > 1 && scores[0][1] === scores[1][1]) {
    if (/[ãõç]/i.test(value)) return 'pt';
    if (/[ñ¿¡]/i.test(value)) return 'es';
  }
  return scores[0][0];
}

function detectDomains(text) {
  const value = String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const ranked = [];
  for (const [domain, terms] of Object.entries(DOMAIN_LEXICON)) {
    let score = 0;
    for (const term of terms) {
      const normalizedTerm = term.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
      if (value.split(/\s+/).includes(normalizedTerm) || value.includes(' ' + normalizedTerm + ' ')) score++;
    }
    if (score) ranked.push({ domain, score, confidence: Math.min(0.99, 0.55 + score * 0.12) });
  }
  return ranked.sort((a, b) => b.score - a.score);
}

function detectIntent(text) {
  const value = String(text || '');
  const time = /\b(hora|horario|time)\b/i.test(value) || /\bqu[eé]\s+tiempo\s+es\b/i.test(value);
  const weather = /\b(temperatura|clima|tiempo|weather|temperature|forecast|previsao)\b/i.test(value) && !time;
  const duration = /\b(cu[aá]nto\s+tiempo|quanto\s+tempo|how\s+long|demora|dura|duraci[oó]n|duração)\b/i.test(value);
  if (time && !duration) return 'time';
  if (weather && !duration) return 'weather';
  if (duration && !/\b(clima|temperatura|weather|forecast|previs[aã]o)\b/i.test(value)) return 'duration';
  if (/\b(compara|comparar|comparativa|diferencia|versus|vs\.?|alternativas|opciones)\b/i.test(value)) return 'comparison';
  if (/\b(busca|buscar|investiga|investigar|fuentes|search|research)\b/i.test(value)) return 'research';
  if (/\b(c[oó]digo|programa|programar|bug|error|javascript|python|html|css|api)\b/i.test(value)) return 'code';
  return /[?¿]/.test(value) ? 'question' : 'conversation';
}

export function resolveContext(message = '', history = []) {
  const current = analyzeLanguage(message);
  const items = Array.isArray(history)
    ? history.filter(item => item && (item.role === 'user' || item.role === 'assistant')).slice(-8)
    : [];
  const userItems = items.filter(item => item.role === 'user');
  // User turns are the authoritative source for inherited intent/topic.
  // Assistant prose can contain many incidental domain words and should not
  // redefine the user's conversational context.
  const userContextText = userItems.map(item => String(item.content || '')).join(' ');
  const context = analyzeLanguage(userContextText);
  const references = [];
  const value = current.normalized.toLowerCase();

  // Only explicit anaphora/follow-up markers should inherit prior context.
  // Generic English words such as "it" or "this" are intentionally excluded
  // because they create false context links in otherwise independent queries.
  if (/\b(aqu[ií]|all[ií]|allá|isso|isto|esse|essa|ese|esa|ese precio|ese valor|esa empresa|esa opción|esa opci[oó]n|eso|isso|aquilo|that one|those|them|there)\b/i.test(value)) references.push('prior_context');
  if (/\b(ahora|hoy|mañana|manana|ayer|agora|hoje|amanhã|ontem|today|tomorrow|yesterday)\b/i.test(value)) references.push('temporal');
  if (/^\s*(?:y|e|and|tamb[ié]n|tambem|também|¿?cu[aá]nto|quanto|how much|how long|y cu[aá]nto|e quanto)\b/i.test(value)) references.push('follow_up');

  const recentUserText = userItems.slice(-4).map(item => String(item.content || '')).join(' ');
  const topicTokens = meaningfulContextTokens(recentUserText);
  const inheritedEntities = extractContextEntities(recentUserText);
  const inheritedDomains = context.domains || [];
  const needsTopic = references.includes('prior_context') || references.includes('follow_up') ||
    /\b(cu[aá]nto|quanto|how much|how long|cu[aá]nto tiempo|quanto tempo|how much time)\b/i.test(value);
  const searchQuery = needsTopic && topicTokens.length
    ? [current.normalized, topicTokens.slice(0, 8).join(' ')].filter(Boolean).join(' ').trim()
    : current.normalized;

  const explicitReference = references.includes('prior_context') || references.includes('follow_up');
  const usableInheritedContext = Boolean(
    inheritedEntities.length ||
    inheritedDomains.length ||
    topicTokens.length >= 2
  );
  const confidence = explicitReference && usableInheritedContext
    ? 0.94
    : explicitReference ? 0.68 : 0.55;

  return {
    references,
    inherited_locations: context.entities?.locations || [],
    inherited_domains: inheritedDomains,
    inherited_entities: inheritedEntities,
    recent_topic_terms: topicTokens.slice(0, 12),
    search_query: searchQuery,
    context_turns: items.length,
    user_turns: userItems.length,
    confidence,
    context_quality: {
      explicit_reference: explicitReference,
      usable: usableInheritedContext,
      inherited_entity_count: inheritedEntities.length,
      inherited_domain_count: inheritedDomains.length,
      topic_term_count: topicTokens.length
    }
  };
}

function meaningfulContextTokens(text = '') {
  const stop = new Set([
    'que','qué','como','cómo','para','por','con','una','uno','unos','unas','del','de','la','el','los','las',
    'este','esta','eso','esa','ese','esto','aqui','aquí','allí','alli','hoy','ahora','puede','puedo','quiero',
    'dime','sobre','entre','desde','hasta','tambien','también','y','o','e','and','the','this','that','how',
    'much','long','what','when','where','why'
  ]);
  return [...new Set(
    String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
      .match(/[a-z0-9][a-z0-9._/-]{2,}/g)?.filter(token => !stop.has(token)) || []
  )];
}

function extractContextEntities(text = '') {
  const value = String(text || '');
  const entities = [];
  const patterns = [
    /\b(?:rtx\s*\d{3,4}|gtx\s*\d{3,4}|rx\s*\d{3,4}|iphone\s*\d{1,3}|galaxy\s+s?\d{1,3})\b/ig,
    /\b(?:meta|apple|microsoft|google|openai|nvidia|amd|intel|bitcoin|ethereum|tesla)\b/ig
  ];
  for (const pattern of patterns) {
    for (const match of value.matchAll(pattern)) {
      const item = String(match[0] || '').trim();
      if (item && !entities.some(existing => existing.toLowerCase() === item.toLowerCase())) entities.push(item);
    }
  }
  return entities;
}

function extractEntities(text) {
  const value = String(text || '');
  const locations = [];
  const locationPatterns = [
    /\b(esteio|porto alegre|canoas|s[aã]o leopoldo|novo hamburgo|gramado|caxias do sul|rio grande do sul)\b/ig,
    /\b(?:en|em|in)\s+([A-ZÁÉÍÓÚÃÕÇ][\p{L}]+(?:\s+[A-ZÁÉÍÓÚÃÕÇ][\p{L}]+){0,3})/gu
  ];
  for (const pattern of locationPatterns) {
    for (const match of value.matchAll(pattern)) {
      const candidate = String(match[1] || match[0]).trim().replace(/^(en|em|in)\s+/i, '');
      if (candidate && !locations.some(item => item.toLowerCase() === candidate.toLowerCase())) locations.push(candidate);
    }
  }
  return { locations };
}
