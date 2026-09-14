/**
 * Canonical capability boundary for the Supracerebro core.
 *
 * Capability is part of execution context, not provider behavior. Every core
 * layer uses this allowlist so specialized context cannot silently cross into
 * another capability.
 */

export const CAPABILITIES = Object.freeze(['general', 'enterprise', 'jobia', 'sbt']);

export function normalizeCapability(value, fallback = 'general') {
  const candidate = String(value ?? '').trim().toLowerCase();
  return CAPABILITIES.includes(candidate) ? candidate : fallback;
}

export function resolveCapability(input = {}) {
  const explicit = input.capability ?? input.metadata?.capability ?? input['x-bitey-capability'];
  if (explicit) return normalizeCapability(explicit);
  return normalizeCapability(input.classifiedCapability ?? 'general');
}

export function capabilityOf(value, fallback = null) {
  if (typeof value === 'string') return CAPABILITIES.includes(value) ? value : fallback;
  if (!value || typeof value !== 'object') return fallback;
  return normalizeCapability(
    value.capability ?? value.routing ?? value['x-bitey-capability'],
    fallback,
  );
}

export function isCapabilityAllowed(value, target) {
  const source = capabilityOf(value, null);
  const normalizedTarget = normalizeCapability(target);
  return source === normalizedTarget || (normalizedTarget === 'general' && source === null);
}

export function filterByCapability(values, targetCapability = 'general') {
  if (!Array.isArray(values)) return [];
  return values.filter(value => isCapabilityAllowed(value, targetCapability));
}

export function scopeResult(value, capability) {
  if (value == null) return value;
  if (Array.isArray(value)) return filterByCapability(value, capability);
  if (typeof value !== 'object') return value;

  const tagged = capabilityOf(value, null);
  const target = normalizeCapability(capability);
  return tagged === target || (target === 'general' && tagged === null) ? value : null;
}
