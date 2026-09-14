import { classifyCapability, shouldDelegate, mergeCapabilityResult } from './capability-router.js';

describe('Bitey capability router', () => {
  test('routes work requests to JobIA', () => {
    expect(classifyCapability('Ayúdame a encontrar trabajo remoto de soporte técnico').capability).toBe('jobia');
  });

  test('keeps conceptual JobIA requests in JobIA', () => {
    expect(classifyCapability('¿Cómo hago un CV para conseguir trabajo?').capability).toBe('jobia');
    expect(classifyCapability('¿Cómo postular a un empleo remoto?').capability).toBe('jobia');
  });

  test('routes trading requests to SBT', () => {
    expect(classifyCapability('Analiza EUR/USD y diseña una estrategia de trading').capability).toBe('sbt');
  });

  test('routes real gold quote requests to SBT', () => {
    expect(classifyCapability('Hola, ¿me puedes mostrar cómo está cotizado el oro?').capability).toBe('sbt');
    expect(classifyCapability('¿Cuál es el precio actual de XAUUSD?').capability).toBe('sbt');
  });

  test('keeps conceptual crypto education in Bitey Core', () => {
    expect(classifyCapability('¿Qué es Bitcoin?').capability).toBe('general');
    expect(classifyCapability('¿Cómo funciona Bitcoin?').capability).toBe('general');
    expect(classifyCapability('Explícame qué es el trading').capability).toBe('general');
  });

  test('routes actionable crypto investment requests to SBT', () => {
    expect(classifyCapability('¿Cómo invertir en Bitcoin?').capability).toBe('sbt');
  });

  test('routes marketing and growth requests to Enterprise', () => {
    expect(classifyCapability('Hazme una estrategia de marketing para mi negocio').capability).toBe('enterprise');
    expect(classifyCapability('Necesito una campaña para captar clientes').capability).toBe('enterprise');
    expect(classifyCapability('Ayúdame a mejorar el SEO de mi empresa').capability).toBe('enterprise');
    expect(classifyCapability('Quiero generar leads y organizar mi CRM').capability).toBe('enterprise');
    expect(classifyCapability('Crea contenido para Instagram de mi negocio').capability).toBe('enterprise');
  });

  test('does not route BiteFixes operational support to Enterprise', () => {
    expect(classifyCapability('Tengo un ticket de BiteFixes').capability).toBe('general');
    expect(classifyCapability('Revisa el portal de soporte de BiteFixes').capability).toBe('general');
    expect(classifyCapability('Necesito atender a un cliente de BiteFixes').capability).toBe('general');
    expect(classifyCapability('¿Cuál es el estado de este ticket de cliente?').capability).toBe('general');
  });

  test('keeps general conversation in Bitey Core', () => {
    expect(classifyCapability('Hola, ¿cómo estás?').capability).toBe('general');
  });

  test('prevents a specialized delegation loop', () => {
    const headers = new Headers({ 'x-bitey-capability': 'jobia' });
    expect(shouldDelegate('Busca un trabajo para mí', headers).delegate).toBe(false);
  });

  test('prevents an Enterprise delegation loop', () => {
    const headers = new Headers({ 'x-bitey-capability': 'enterprise' });
    expect(shouldDelegate('Crea una campaña de marketing', headers).delegate).toBe(false);
  });

  test('normalizes specialized result metadata', () => {
    expect(mergeCapabilityResult({ answer: 'resultado' }, 'sbt')).toMatchObject({
      answer: 'resultado', capability: 'sbt', routed_by: 'bitey-capability-router'
    });
  });
});
