import { classifyHistoryMessage, filterConversationHistory } from './conversation-isolation.js';

describe('conversation isolation', () => {
  test('classifies specialized history', () => {
    expect(classifyHistoryMessage('Quiero hacer backtesting en MT5')).toBe('sbt');
    expect(classifyHistoryMessage('Necesito mejorar mi CV para un empleo remoto')).toBe('jobia');
    expect(classifyHistoryMessage('Necesito revisar un ticket de cliente de BiteFixes')).toBe('enterprise');
    expect(classifyHistoryMessage('Explícame qué es una base de datos')).toBe('general');
  });

  test('removes SBT turns from General history', () => {
    const history = [
      { role: 'user', content: 'Analiza mi estrategia de trading' },
      { role: 'assistant', content: 'La estrategia tiene un drawdown elevado.' },
      { role: 'user', content: 'Explícame qué es Docker' },
      { role: 'assistant', content: 'Docker es una plataforma de contenedores.' }
    ];
    expect(filterConversationHistory(history, 'general')).toEqual([history[2], history[3]]);
  });

  test('removes JobIA turns from General history', () => {
    const history = [
      { role: 'user', content: 'Ayúdame con mi CV para conseguir trabajo' },
      { role: 'assistant', content: 'Podemos mejorar el resumen profesional.' },
      { role: 'user', content: '¿Qué es PostgreSQL?' },
      { role: 'assistant', content: 'PostgreSQL es un sistema de base de datos.' }
    ];
    expect(filterConversationHistory(history, 'general')).toEqual([history[2], history[3]]);
  });

  test('removes Enterprise turns from General history', () => {
    const history = [
      { role: 'user', content: 'Necesito revisar un ticket de cliente de BiteFixes' },
      { role: 'assistant', content: 'Revisemos el estado del ticket empresarial.' },
      { role: 'user', content: 'Explícame qué es Docker' },
      { role: 'assistant', content: 'Docker es una plataforma de contenedores.' }
    ];
    expect(filterConversationHistory(history, 'general')).toEqual([history[2], history[3]]);
  });

  test('preserves only SBT turns for SBT', () => {
    const history = [
      { role: 'user', content: 'Analiza EUR/USD' },
      { role: 'assistant', content: 'Señal técnica de ejemplo.' },
      { role: 'user', content: 'Ayúdame con mi CV' },
      { role: 'assistant', content: 'Podemos mejorar tu CV.' }
    ];
    expect(filterConversationHistory(history, 'sbt')).toEqual([history[0], history[1]]);
  });

  test('preserves only JobIA turns for JobIA', () => {
    const history = [
      { role: 'user', content: 'Quiero buscar un empleo remoto' },
      { role: 'assistant', content: 'Revisemos tu perfil profesional.' },
      { role: 'user', content: 'Analiza Bitcoin' },
      { role: 'assistant', content: 'Información de mercado.' }
    ];
    expect(filterConversationHistory(history, 'jobia')).toEqual([history[0], history[1]]);
  });

  test('preserves only Enterprise turns for Enterprise', () => {
    const history = [
      { role: 'user', content: 'Necesito revisar un ticket de cliente de BiteFixes' },
      { role: 'assistant', content: 'El ticket pertenece al portal de soporte.' },
      { role: 'user', content: 'Analiza Bitcoin' },
      { role: 'assistant', content: 'Información de mercado.' },
      { role: 'user', content: 'Ayúdame con mi CV' },
      { role: 'assistant', content: 'Podemos mejorar tu CV.' }
    ];
    expect(filterConversationHistory(history, 'enterprise')).toEqual([history[0], history[1]]);
  });

  test('keeps Enterprise history out of SBT and JobIA', () => {
    const history = [
      { role: 'user', capability: 'enterprise', content: 'Revisemos el portal de soporte de BiteFixes' },
      { role: 'assistant', capability: 'enterprise', content: 'De acuerdo.' }
    ];
    expect(filterConversationHistory(history, 'sbt')).toEqual([]);
    expect(filterConversationHistory(history, 'jobia')).toEqual([]);
    expect(filterConversationHistory(history, 'general')).toEqual([]);
  });

  test('explicit capability metadata overrides text classification', () => {
    const history = [
      { role: 'user', capability: 'general', content: 'Bitcoin es un tema que quiero estudiar' },
      { role: 'assistant', capability: 'general', content: 'Podemos estudiarlo desde una perspectiva educativa.' }
    ];
    expect(filterConversationHistory(history, 'general')).toEqual(history);
    expect(filterConversationHistory(history, 'sbt')).toEqual([]);
  });
});
