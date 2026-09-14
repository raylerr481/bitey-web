/** Capability-scoped web-research boundary. Search providers are injected. */

import { capabilityOf, normalizeCapability, scopeResult } from './capability-boundary.js';

export class ResearchEngine {
  constructor({ providers = [] } = {}) {
    this.providers = providers;
  }

  async investigate(request = {}, context = {}, memory = []) {
    const capability = normalizeCapability(request.capability);
    const results = [];

    for (const provider of this.providers) {
      if (!provider?.search) continue;
      const providerCapability = capabilityOf(provider, null);
      if (capability !== 'general' && providerCapability !== capability) continue;
      if (capability === 'general' && providerCapability && providerCapability !== 'general') continue;

      const result = await provider.search({ request, context, memory });
      const scoped = Array.isArray(result)
        ? result.filter(item => capabilityOf(item, null) === capability || (capability === 'general' && !capabilityOf(item, null)))
        : scopeResult(result, capability);

      if (scoped != null) results.push(scoped);
    }

    return { capability, results };
  }
}
