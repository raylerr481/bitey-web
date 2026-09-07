import { classifyCapability, shouldDelegate, mergeCapabilityResult } from './capability-router.js';

describe('Bitey capability router', () => {
  test('routes work requests to JobIA', () => {
    expect(classifyCapability('Ayúdame a encontrar trabajo remoto de soporte técnico').capability).toBe('jobia');
  });

  test('routes trading requests to SBT', () => {
    expect(classifyCapability('Analiza EUR/USD y diseña una estrategia de trading').capability).toBe('sbt');
  });

  test('routes real gold quote requests to SBT', () => {
    expect(classifyCapability('Hola, ¿me puedes mostrar cómo está cotizado el oro?').capability).toBe('sbt');
    expect(classifyCapability('¿Cuál es el precio actual de XAUUSD?').capability).toBe('sbt');
  });

  test('keeps general conversation in Bitey Core', () => {
    expect(classifyCapability('Hola, ¿cómo estás?').capability).toBe('general');
  });

  test('prevents a specialized delegation loop', () => {
    const headers = new Headers({ 'x-bitey-capability': 'jobia' });
    expect(shouldDelegate('Busca un trabajo para mí', headers).delegate).toBe(false);
  });

  test('normalizes specialized result metadata', () => {
    expect(mergeCapabilityResult({ answer: 'resultado' }, 'sbt')).toMatchObject({
      answer: 'resultado', capability: 'sbt', routed_by: 'bitey-capability-router'
    });
  });
});
