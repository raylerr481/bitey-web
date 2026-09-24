const DICTIONARY = new Map([
  ['q','que'], ['k','que'], ['pq','porque'], ['xq','porque'],
  ['tb','tambien'], ['tmb','tambien'], ['dnd','donde'], ['qdo','cuando'],
  ['cm','como'], ['ola','hola'], ['holaa','hola'],
  ['timepoe','tiempo'], ['tiempoe','tiempo'], ['tiempe','tiempo'],
  ['temp','temperatura'], ['tempertaura','temperatura'], ['temperatua','temperatura'],
  ['cliam','clima'], ['clm','clima'], ['previsao','previsao'], ['previsaoo','previsao'],
  ['wheather','weather'], ['weater','weather'], ['teh','the'],
  ['mercdo','mercado'], ['mercaod','mercado'], ['cotizacoin','cotizacion'],
  ['infomacion','informacion'], ['informcaion','informacion'],
  ['tecnologia','tecnologia'], ['inteligenciaartificial','inteligencia artificial']
]);

const SEMANTIC_TERMS = [
  'temperatura','clima','tiempo','tempo','weather','temperature','forecast','previsao',
  'mercado','trading','bitcoin','acciones','bolsa','empleo','trabajo','vacante',
  'curriculum','codigo','programacion','wordpress','linux','windows','docker'
];

const LANGUAGE_MARKERS = {
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
  const entities = extractEntities(normalized);
  const confidence = corrections.length ? Math.min(0.99, 0.86 + Math.min(corrections.length, 4) * 0.03) : 0.98;

  return { original, normalized, language, intent, entities, corrections, confidence };
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
  const scores = Object.entries(LANGUAGE_MARKERS).map(([language, pattern]) => [
    language,
    (value.match(new RegExp(pattern.source, 'gi')) || []).length
  ]).sort((a, b) => b[1] - a[1]);
  if (!scores.length || scores[0][1] === 0) return 'unknown';
  if (scores.length > 1 && scores[0][1] === scores[1][1]) {
    if (/[ãõç]|\b(uma|onde|quando|previsao|tempo em)\b/i.test(value)) return 'pt';
    if (/[ñ¿¡]|\b(una|donde|cuando|qué|cómo)\b/i.test(value)) return 'es';
  }
  return scores[0][0];
}

function detectIntent(text) {
  const value = String(text || '');
  const weather = /\b(temperatura|clima|tiempo|weather|temperature|forecast|previsao)\b/i.test(value);
  const duration = /\b(cu[aá]nto\s+tiempo|quanto\s+tempo|how\s+long|demora|dura|duraci[oó]n|duração)\b/i.test(value);
  if (weather && !duration) return 'weather';
  if (duration && !/\b(clima|temperatura|weather|forecast|previs[aã]o)\b/i.test(value)) return 'duration';
  if (/\b(compara|comparar|comparativa|diferencia|versus|vs\.?|alternativas|opciones)\b/i.test(value)) return 'comparison';
  if (/\b(busca|buscar|investiga|investigar|fuentes|search|research)\b/i.test(value)) return 'research';
  if (/\b(c[oó]digo|programa|programar|bug|error|javascript|python|html|css|api)\b/i.test(value)) return 'code';
  return /[?¿]/.test(value) ? 'question' : 'conversation';
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
