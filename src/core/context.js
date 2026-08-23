/** Provider-neutral context boundary for Bitey IA. */
export class ContextEngine {
  constructor({ sources = [] } = {}) {
    this.sources = sources;
  }

  async resolve(request) {
    const results = [];
    for (const source of this.sources) {
      if (source?.resolve) {
        const value = await source.resolve(request);
        if (value != null) results.push(value);
      }
    }
    return { sources: results };
  }
}
