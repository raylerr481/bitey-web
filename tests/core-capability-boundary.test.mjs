import test from 'node:test';
import assert from 'node:assert/strict';

import { ContextEngine } from '../src/core/context.js';
import { MemoryEngine } from '../src/core/memory.js';
import { ResearchEngine } from '../src/core/research.js';
import { BiteySupracerebro } from '../src/core/suprabrain.js';

const source = (capability, value) => ({ capability, async resolve() { return value; } });
const provider = (capability, value) => ({ capability, async search() { return value; } });

test('general context excludes specialized sources', async () => {
  const engine = new ContextEngine({
    sources: [
      source('general', { capability: 'general', text: 'general' }),
      source('enterprise', { capability: 'enterprise', text: 'enterprise-secret' }),
      source('sbt', { capability: 'sbt', text: 'sbt-secret' }),
    ],
  });

  const result = await engine.resolve({ capability: 'general' });
  assert.deepEqual(result.sources, [{ capability: 'general', text: 'general' }]);
});

test('specialized context only resolves the matching source', async () => {
  const engine = new ContextEngine({
    sources: [
      source('enterprise', { capability: 'enterprise', text: 'enterprise' }),
      source('sbt', { capability: 'sbt', text: 'sbt' }),
      source('jobia', { capability: 'jobia', text: 'jobia' }),
    ],
  });

  const result = await engine.resolve({ capability: 'enterprise' });
  assert.deepEqual(result.sources, [{ capability: 'enterprise', text: 'enterprise' }]);
});

test('specialized memory rejects untagged and cross-capability entries', async () => {
  const engine = new MemoryEngine({
    adapter: {
      async recall() {
        return [
          { capability: 'enterprise', text: 'enterprise' },
          { capability: 'sbt', text: 'sbt' },
          { text: 'untagged' },
        ];
      },
    },
  });

  const result = await engine.recall({ capability: 'enterprise' }, {});
  assert.deepEqual(result, [{ capability: 'enterprise', text: 'enterprise' }]);
});

test('general memory preserves legacy untagged entries', async () => {
  const engine = new MemoryEngine({
    adapter: {
      async recall() {
        return [{ text: 'legacy-general' }, { capability: 'sbt', text: 'sbt' }];
      },
    },
  });

  const result = await engine.recall({ capability: 'general' }, {});
  assert.deepEqual(result, [{ text: 'legacy-general' }]);
});

test('research providers are capability-scoped', async () => {
  const engine = new ResearchEngine({
    providers: [
      provider('enterprise', { capability: 'enterprise', text: 'enterprise' }),
      provider('sbt', { capability: 'sbt', text: 'sbt' }),
    ],
  });

  const result = await engine.investigate({ capability: 'sbt' }, {}, []);
  assert.deepEqual(result.results, [{ capability: 'sbt', text: 'sbt' }]);
});

test('supracerebro classifies and carries capability into the provider packet', async () => {
  let packet;
  const brain = new BiteySupracerebro({
    context: { async resolve(request) { return { capability: request.capability, sources: [] }; } },
    memory: { async recall() { return []; } },
    providers: [{ async complete(value) { packet = value; return { ok: true }; } }],
  });

  await brain.think({ message: 'Necesito una estrategia de marketing para mi negocio' });
  assert.equal(packet.request.capability, 'enterprise');
});

test('explicit capability overrides message classification', async () => {
  let packet;
  const brain = new BiteySupracerebro({
    providers: [{ async complete(value) { packet = value; return { ok: true }; } }],
  });

  await brain.think({
    capability: 'general',
    message: 'Necesito una estrategia de marketing para mi negocio',
  });
  assert.equal(packet.request.capability, 'general');
});
