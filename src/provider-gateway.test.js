import { providerStatus } from './provider-gateway.js';

describe('Bitey free cognitive provider gateway', () => {
  test('uses only free providers and excludes deprecated Qwen defaults', () => {
    const status = providerStatus({});
    expect(status.policy).toBe('groq-openrouter-free-only-no-paid-fallback');
    expect(status.groq.model).toBe('openai/gpt-oss-120b');
    expect(status.openrouter.model).toBe('nvidia/nemotron-3-ultra-550b-a55b:free');
    expect(status.groq.model).not.toMatch(/qwen/i);
    expect(status.openrouter.model).not.toMatch(/qwen/i);
  });

  test('keeps provider credentials out of status output', () => {
    const status = providerStatus({
      GROQ_API_KEY: 'secret-groq',
      OPENROUTER_API_KEY: 'secret-openrouter'
    });
    expect(JSON.stringify(status)).not.toContain('secret-groq');
    expect(JSON.stringify(status)).not.toContain('secret-openrouter');
  });
});
