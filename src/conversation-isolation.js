import { classifyCapability } from './capability-router.js';

export function classifyHistoryMessage(content) {
  return classifyCapability(content).capability;
}

function explicitCapability(item) {
  const value = item?.capability || item?.routing || item?.['x-bitey-capability'];
  if (value === 'enterprise' || value === 'jobia' || value === 'sbt' || value === 'general') return value;
  return null;
}

function isAllowedCapability(capability, target) {
  if (target === 'general') return capability === 'general';
  return capability === target;
}

export function filterConversationHistory(history, targetCapability = 'general') {
  if (!Array.isArray(history)) return [];
  const target = ['general', 'enterprise', 'jobia', 'sbt'].includes(targetCapability) ? targetCapability : 'general';
  const filtered = [];
  let pendingUserCapability = 'general';

  for (const item of history) {
    if (!item || !['user', 'assistant'].includes(item.role)) continue;
    const explicit = explicitCapability(item);

    if (item.role === 'user') {
      pendingUserCapability = explicit || classifyHistoryMessage(item.content);
      if (isAllowedCapability(pendingUserCapability, target)) filtered.push(item);
      continue;
    }

    const assistantCapability = explicit || pendingUserCapability;
    if (isAllowedCapability(assistantCapability, target)) filtered.push(item);
  }

  return filtered;
}
