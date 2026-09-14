const ENTERPRISE_INTENT = /\b(bitey\s*enterprise|bitey\s*empresarial|estrategia de marketing|marketing digital|marketing para (?:mi|un|el) negocio|campaña de marketing|campaña publicitaria|publicidad para (?:mi|un|el) negocio|posicionamiento (?:web|seo)|seo para (?:mi|un|el) negocio|contenido para (?:mis|las|redes) sociales|redes sociales para (?:mi|un|el) negocio|generar leads|generación de leads|captar clientes|captación de clientes|embudo de ventas|funnel de ventas|organizar mi crm|implementar crm|estrategia comercial|automatización comercial|automatizar ventas|automatización de marketing|marketing automation)\b/i;
const ENTERPRISE_DOMAIN = /\b(marketing|seo|publicidad|crm|ventas|leads|campañas?|contenido|redes sociales|automatización comercial|automatización de marketing)\b/i;
const ENTERPRISE_ACTION = /\b(haz|hacer|crea|crear|diseña|diseñar|mejora|mejorar|genera|generar|captar|captación|organiza|organizar|automatiza|automatizar|implementa|implementar|planifica|planificar|estrategia|estrategia)\b/i;
const ENTERPRISE_CONTEXT = /\b(negocio|empresa|empresarial|comercial|clientes|cliente|marca|ventas|marketing)\b/i;
const JOBIA_KEYWORDS = /\b(empleo|empleos|trabajo|trabajos|vacante|vacantes|curr[ií]culum|cv|carta de presentaci[oó]n|entrevista laboral|entrevista de trabajo|postulaci[oó]n|postular|contrataci[oó]n|salario|sueldo|profesi[oó]n|carrera profesional|job|jobs|career|resume|cover letter)\b/i;
const SBT_KEYWORDS = /\b(trading|trader|forex|divisas|mercado financiero|mercados financieros|acciones|bolsa|crypto|criptomonedas|bitcoin|eur\/usd|usd\/brl|xau\/usd|xauusd|gold|oro|precio del oro|cotizaci[oó]n del oro|oro hoy|estrategia de trading|estrategia de mercado|backtest|backtesting|bot de trading|bot trading|robot de trading|mt5|metatrader|tradingview|alpaca|riesgo de trading|paper trading|demo trading)\b/i;
const CONCEPTUAL = /\b(qu[eé]|cu[aá]l|cu[aá]les|c[oó]mo|como|significa|definici[oó]n|define|explica|expl[ií]ca|expl[ií]came|what|which|how|meaning|definition|explain)\b/i;
const TRADING_ACTION = /\b(invertir|compra|comprar|vende|vender|operar|opera|trade|trading|ejecutar|ejecuci[oó]n|orden|[oó]rdenes|backtest|backtesting|bot|robot|señal|se[nñ]al)\b/i;

export function classifyCapability(message = '') {
  const text = String(message).trim();
  if (!text) return { capability: 'general', confidence: 1, reason: 'empty_or_general', specialized: false };

  const explicitEnterprise = ENTERPRISE_INTENT.test(text) ||
    (ENTERPRISE_DOMAIN.test(text) && ENTERPRISE_ACTION.test(text) && ENTERPRISE_CONTEXT.test(text));
  if (explicitEnterprise) return { capability: 'enterprise', confidence: 0.97, reason: 'enterprise_marketing_intent', specialized: true };

  const hasSbtDomain = SBT_KEYWORDS.test(text);
  if (CONCEPTUAL.test(text) && hasSbtDomain && !TRADING_ACTION.test(text)) {
    return { capability: 'general', confidence: 0.92, reason: 'conceptual_sbt_question', specialized: false };
  }

  if (hasSbtDomain) return { capability: 'sbt', confidence: 0.96, reason: 'sbt_domain', specialized: true };
  if (JOBIA_KEYWORDS.test(text)) return { capability: 'jobia', confidence: 0.96, reason: 'jobia_domain', specialized: true };
  return { capability: 'general', confidence: 0.9, reason: 'general_domain', specialized: false };
}

export function shouldDelegate(message = '', headers) {
  const classification = classifyCapability(message);
  const delegated = String(headers?.get?.('x-bitey-capability') || '').toLowerCase();
  if (delegated === 'jobia' || delegated === 'sbt' || delegated === 'enterprise') {
    return { ...classification, capability: delegated, delegate: false, reason: 'already_delegated' };
  }
  return { ...classification, delegate: classification.specialized };
}

export function mergeCapabilityResult(result = {}, capability = 'general') {
  return { ...result, capability, routed_by: 'bitey-capability-router' };
}
