/**
 * Provider-neutral AI registry.
 *
 * Bitey IA owns orchestration; providers are replaceable collaborators.
 * Credentials and provider-specific configuration stay outside this module.
 */
export class ProviderRegistry {
  constructor(providers = []) {
    this.providers = new Map();
    providers.forEach(provider => this.register(provider));
  }

  register(provider) {
    if (!provider?.name) throw new Error('Provider name is required');
    this.providers.set(provider.name, provider);
    return provider;
  }

  available() {
    return [...this.providers.values()].filter(provider => provider.available !== false);
  }

  select(preferred = []) {
    const available = this.available();
    for (const name of preferred) {
      const match = available.find(provider => provider.name === name);
      if (match) return match;
    }
    return available[0] ?? null;
  }
}
