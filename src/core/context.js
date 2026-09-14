/** Capability-scoped context boundary for Bitey IA. */

import { capabilityOf, filterByCapability, normalizeCapability, scopeResult } from './capability-boundary.js';

export class ContextEngine {
  constructor({ sources = [] } = {}) {
    this.sources = sources;
  }

  async resolve(request = {}) {
    const capability = normalizeCapability(request.capability);
    const results = [];

    for (const source of this.sources) {
      if (!source?.resolve) continue;

      const sourceCapability = capabilityOf(source, null);
      // Untagged sources are safe only for General. Specialized requests must
      // opt in explicitly, preventing accidental cross-module context reuse.
      if (capability !== 'general' && sourceCapability !== capability) continue;
      if (capability === 'general' && sourceCapability && sourceCapability !== 'general') continue;

      const value = await source.resolve(request);
      const scoped = Array.isArray(value)
        ? filterByCapability(value, capability)
        : scopeResult(value, capability);

      if (scoped != null) results.push(scoped);
    }

    return { capability, sources: results };
  }
}
