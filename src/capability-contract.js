const DEFAULT_TIMEOUT_MS = 9000;

function originFromEnv(env, key) {
  const value = String(env?.[key] || '').trim();
  return value ? value.replace(/\/+$/, '') : '';
}

function timeoutFromEnv(env) {
  const value = Number(env?.BITEY_CAPABILITY_TIMEOUT_MS || DEFAULT_TIMEOUT_MS);
  return Number.isFinite(value) && value >= 1000 && value <= 15000 ? Math.floor(value) : DEFAULT_TIMEOUT_MS;
}

function specializedPath(capability) {
  if (capability === 'jobia') return '/api/v1/capabilities/delegate';
  if (capability === 'sbt') return '/api/v1/capabilities/delegate';
  return '';
}

export async function delegateCapability({ request, env, requestId, capability, message, conversationId = '' }) {
  const envKey = capability === 'jobia' ? 'JOBIA_API_ORIGIN' : capability === 'sbt' ? 'SBT_API_ORIGIN' : '';
  const origin = originFromEnv(env, envKey);
  if (!origin) return { handled: false, configured: false, reason: 'specialized_origin_not_configured' };

  const path = specializedPath(capability);
  if (!path) return { handled: false, configured: false, reason: 'unsupported_capability' };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort('capability_timeout'), timeoutFromEnv(env));
  try {
    const headers = new Headers({
      'content-type': 'application/json',
      'accept': 'application/json',
      'x-bitey-channel': 'web',
      'x-bitey-origin': 'cloudflare',
      'x-bitey-capability': capability,
      'x-bitey-routing': `specialized:${capability}`,
      'x-bitey-request-id': requestId,
      'x-bitey-hop': '1',
    });
    const upstream = await fetch(`${origin}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        contract: capability === 'jobia' ? 'jobia-v1' : 'sbt-v1',
        capability,
        message,
        conversation_id: conversationId || null,
        source: 'bitey-web',
        mode: capability === 'sbt' ? 'research-only' : 'specialized',
      }),
      signal: controller.signal,
    });
    const raw = await upstream.text();
    let body = null;
    try { body = JSON.parse(raw); } catch (_) {}
    if (!upstream.ok) return { handled: false, configured: true, reason: 'specialized_upstream_error', status: upstream.status };
    if (!body || typeof body !== 'object') return { handled: false, configured: true, reason: 'specialized_invalid_response' };
    return { handled: true, configured: true, status: upstream.status, body };
  } catch (error) {
    return { handled: false, configured: true, reason: error?.name === 'AbortError' ? 'specialized_timeout' : 'specialized_unavailable' };
  } finally {
    clearTimeout(timer);
  }
}

export function specializedUnavailable(capability, reason, requestId) {
  const label = capability === 'jobia' ? 'JobIA' : 'Bitey SBT';
  return {
    error: 'specialized_capability_unavailable',
    capability,
    delegated: false,
    delegation_status: 'unavailable',
    message: `${label} no está disponible en este momento. Bitey IA no simulará que utilizó esa capacidad especializada.`,
    reason,
    request_id: requestId,
  };
}
