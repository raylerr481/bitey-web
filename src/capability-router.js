const JOBIA_KEYWORDS = /\b(empleo|empleos|trabajo|trabajos|vacante|vacantes|curr[ií]culum|cv|carta de presentaci[oó]n|entrevista laboral|entrevista de trabajo|postulaci[oó]n|postular|contrataci[oó]n|salario|sueldo|profesi[oó]n|carrera profesional|job|jobs|career|resume|cover letter)\b/i;
const SBT_KEYWORDS = /\b(trading|trader|forex|divisas|mercado financiero|mercados financieros|acciones|bolsa|crypto|criptomonedas|bitcoin|eur\/usd|usd\/brl|estrategia de trading|estrategia de mercado|backtest|backtesting|bot de trading|bot trading|robot de trading|mt5|metatrader|tradingview|alpaca|riesgo de trading|paper trading|demo trading)\b/i;

export function classifyCapability(message = '') {
  const text = String(message).trim();
  if (!text) return { capability: 'general', confidence: 1, reason: 'empty_or_general', specialized: false };
  if (SBT_KEYWORDS.test(text)) return { capability: 'sbt', confidence: 0.96, reason: 'trading_domain', specialized: true };
  if (JOBIA_KEYWORDS.test(text)) return { capability: 'jobia', confidence: 0.96, reason: 'work_domain', specialized: true };
  return { capability: 'general', confidence: 1, reason: 'general_domain', specialized: false };
}

export function shouldDelegate(message = '', headers) {
  const classification = classifyCapability(message);
  const delegated = String(headers?.get?.('x-bitey-capability') || '').toLowerCase();
  if (delegated === 'jobia' || delegated === 'sbt') {
    return { ...classification, capability: delegated, delegate: false, reason: 'already_delegated' };
  }
  return { ...classification, delegate: classification.specialized };
}

export function capabilityHeaders(capability) {
  const headers = new Headers();
  headers.set('X-Bitey-Capability', capability);
  headers.set('X-Bitey-Routing', capability === 'general' ? 'core' : `specialized:${capability}`);
  return headers;
}

export function mergeCapabilityResult(payload, capability) {
  const body = payload && typeof payload === 'object' ? payload : { answer: String(payload ?? '') };
  return {
    ...body,
    capability: capability || body.capability || 'general',
    routed_by: 'bitey-capability-router',
  };
}
