/** Minimal memory boundary. Persistence belongs behind an adapter. */
export class MemoryEngine {
  constructor({ adapter = null } = {}) {
    this.adapter = adapter;
  }

  async recall(request, context) {
    return this.adapter?.recall?.({ request, context }) ?? [];
  }

  async remember(entry) {
    return this.adapter?.remember?.(entry) ?? null;
  }
}
