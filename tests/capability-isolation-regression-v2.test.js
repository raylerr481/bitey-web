import { classifyCapability } from '../src/capability-router.js';
import { filterConversationHistory } from '../src/conversation-isolation.js';

describe('capability isolation regression', () => {
  test('general excludes SBT and JobIA history', () => {
    const history = [
      { role: 'user', content: 'Analiza mi estrategia de trading' },
      { role: 'assistant', content: 'SBT response' },
      { role: 'user', content: 'Mejora mi CV para empleo remoto' },
      { role: 'assistant', content: 'JobIA response' },
      { role: 'user', content: 'Explícame Docker' },
      { role: 'assistant', content: 'Docker response' }
    ];
    expect(filterConversationHistory(history, 'general')).toEqual([history[4], history[5]]);
  });

  test('SBT receives only SBT history', () => {
    const history = [
      { role: 'user', content: 'Analiza EUR/USD' },
      { role: 'assistant', content: 'SBT response' },
      { role: 'user', content: 'Necesito trabajo remoto' },
      { role: 'assistant', content: 'JobIA response' }
    ];
    expect(filterConversationHistory(history, 'sbt')).toEqual([history[0], history[1]]);
  });

  test('JobIA receives only JobIA history', () => {
    const history = [
      { role: 'user', content: 'Quiero un empleo remoto' },
      { role: 'assistant', content: 'JobIA response' },
      { role: 'user', content: 'Analiza Bitcoin' },
      { role: 'assistant', content: 'SBT response' }
    ];
    expect(filterConversationHistory(history, 'jobia')).toEqual([history[0], history[1]]);
  });

  test('Bitcoin education stays General while investment intent routes to SBT', () => {
    expect(classifyCapability('¿Qué es Bitcoin?').capability).toBe('general');
    expect(classifyCapability('¿Cómo invertir en Bitcoin?').capability).toBe('sbt');
  });
});
