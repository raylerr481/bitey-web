const JOBIA_KEYWORDS = /\b(empleo|empleos|trabajo|trabajos|vacante|vacantes|curr[ií]culum|cv|carta de presentaci[oó]n|entrevista laboral|entrevista de trabajo|postulaci[oó]n|postular|contrataci[oó]n|salario|sueldo|profesi[oó]n|carrera profesional|job|jobs|career|resume|cover letter)\b/i;
const SBT_KEYWORDS = /\b(trading|trader|forex|divisas|mercado financiero|mercados financieros|acciones|bolsa|crypto|criptomonedas|bitcoin|eur\/usd|usd\/brl|xau\/usd|xauusd|gold|oro|precio del oro|cotizaci[oó]n del oro|oro hoy|estrategia de trading|estrategia de mercado|backtest|backtesting|bot de trading|bot trading|robot de trading|mt5|metatrader|tradingview|alpaca|riesgo de trading|paper trading|demo trading|invertir|inversi[oó]n)\b/i;

export function classifyHistoryMessage(content) {
  const text = String(content || '').trim();
  if (!text) return 'general';
  if (JOBIA_KEYWORDS.test(text)) return 'jobia';
  if (SBT_KEYWORDS.test(text)) return 'sbt';
  return 'general';
}

function explicitCapability(item) {
  const value = item?.capability || item?.routing || item?.['x-bitey-capability'];
  if (value === 'jobia' || value === 'sbt' || value === 'general') return value;
  return null;
}

function isAllowedCapability(capability, target) {
  if (target === 'general') return capability === 'general';
  return capability === target;
}

export function filterConversationHistory(history, targetCapability = 'general') {
  if (!Array.isArray(history)) return [];
  const target = ['general', 'jobia', 'sbt'].includes(targetCapability) ? targetCapability : 'general';
  const filtered = [];
  let pendingUserCapability = 'general';

  for (const item of history) {
    if (!item || !['user', 'assistant'].includes(item.role)) continue;
    const explicit = explicitCapability(item);

    if (item.role === 'user') {
      pendingUserCapability = explicit || classifyHistoryMessage(item.content);
      if (isAllowedCapability(pendingUserCapability, target)) filtered.push(item);
      continue;
    }

    const assistantCapability = explicit || pendingUserCapability;
    if (isAllowedCapability(assistantCapability, target)) filtered.push(item);
  }

  return filtered;
}
