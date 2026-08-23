/** Web-research boundary. Search providers are injected; no provider is hard-coded. */
export class ResearchEngine {
  constructor({ providers = [] } = {}) {
    this.providers = providers;
  }

  async investigate(request, context, memory) {
    const results = [];
    for (const provider of this.providers) {
      if (!provider?.search) continue;
      const result = await provider.search({ request, context, memory });
      if (result != null) results.push(result);
    }
    return { results };
  }
}
