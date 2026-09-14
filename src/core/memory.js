/** Capability-scoped memory boundary. Persistence belongs behind an adapter. */

import { capabilityOf, filterByCapability, normalizeCapability } from './capability-boundary.js';

export class MemoryEngine {
  constructor({ adapter = null } = {}) {
    this.adapter = adapter;
  }

  async recall(request = {}, context = {}) {
    const capability = normalizeCapability(request.capability);
    const entries = await this.adapter?.recall?.({ request, context }) ?? [];
    return filterByCapability(entries, capability);
  }

  async remember(entry = {}) {
    const capability = capabilityOf(entry, 'general');
    return this.adapter?.remember?.({ ...entry, capability }) ?? null;
  }
}
