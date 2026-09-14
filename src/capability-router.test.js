import { describe, expect, test } from 'vitest';
import { classifyCapability, mergeCapabilityResult, shouldDelegate } from './capability-router.js';

describe('Bitey capability router', () => {
  test('routes JobIA work requests to JobIA', () => {
    expect(classifyCapability('Busca un trabajo remoto para mí').capability).toBe('jobia');
    expect(classifyCapability('Necesito mejorar mi CV para un empleo remoto').capability).toBe('jobia');
  });

  test('routes actionable trading requests to SBT', () => {
    expect(classifyCapability('Haz un backtest de esta estrategia en MT5').capability).toBe('sbt');
    expect(classifyCapability('¿Cuál es el precio de Bitcoin?').capability).toBe('sbt');
    expect(classifyCapability('¿Cómo invertir en Bitcoin?').capability).toBe('sbt');
  });

  test('routes marketing and growth requests to Enterprise', () => {
    expect(classifyCapability('Hazme una estrategia de marketing para mi negocio').capability).toBe('enterprise');
    expect(classifyCapability('Necesito una campaña para captar clientes').capability).toBe('enterprise');
    expect(classifyCapability('Ayúdame a mejorar el SEO de mi empresa').capability).toBe('enterprise');
    expect(classifyCapability('Quiero generar leads y organizar mi CRM').capability).toBe('enterprise');
    expect(classifyCapability('Crea contenido para Instagram de mi negocio').capability).toBe('enterprise');
    expect(classifyCapability('Diseña un embudo de ventas').capability).toBe('enterprise');
    expect(classifyCapability('Automatiza mi marketing').capability).toBe('enterprise');
  });

  test('does not route generic commercial or support words to Enterprise', () => {
    expect(classifyCapability('Tengo un ticket de BiteFixes').capability).toBe('general');
    expect(classifyCapability('Revisa el portal de soporte de BiteFixes').capability).toBe('general');
    expect(classifyCapability('Necesito atender a un cliente de BiteFixes').capability).toBe('general');
    expect(classifyCapability('¿Cuál es el estado de este ticket de cliente?').capability).toBe('general');
    expect(classifyCapability('¿Qué significa CRM?').capability).toBe('general');
    expect(classifyCapability('¿Qué es SEO?').capability).toBe('general');
    expect(classifyCapability('Hola, tengo una duda sobre ventas').capability).toBe('general');
  });

  test('keeps general conversation in Bitey Core', () => {
    expect(classifyCapability('Hola, ¿cómo estás?').capability).toBe('general');
  });

  test('prevents specialized delegation loops', () => {
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
