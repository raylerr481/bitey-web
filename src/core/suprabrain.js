/**
 * Bitey IA — Supracerebro foundation.
 *
 * This module is intentionally provider-neutral and independent from
 * BiteFixes Backend. It defines the orchestration boundary for a complete
 * Bitey intelligence platform without embedding credentials or business data.
 */

import { classifyCapability } from '../capability-router.js';
import { normalizeCapability } from './capability-boundary.js';

export class BiteySupracerebro {
  constructor({ context, memory, research, providers = [], tools = [] } = {}) {
    this.context = context;
    this.memory = memory;
    this.research = research;
    this.providers = providers;
    this.tools = tools;
  }

  async think(input) {
    const request = this.normalize(input);
    const context = await this.context?.resolve?.(request) ?? {};
    const memory = await this.memory?.recall?.(request, context) ?? [];

    let research = null;
    if (request.researchRequired && this.research?.investigate) {
      research = await this.research.investigate(request, context, memory);
    }

    const packet = {
      request,
      context,
      memory,
      research,
      availableTools: this.tools.map(tool => tool.name),
    };

    return this.reason(packet);
  }

  async reason(packet) {
    if (!this.providers.length) {
      return {
        status: 'needs_provider',
        packet,
      };
    }

    const provider = this.providers.find(item => item?.available !== false);
    if (!provider?.complete) {
      return { status: 'needs_provider', packet };
    }

    return provider.complete(packet);
  }

  normalize(input = {}) {
    const message = String(input.message ?? '').trim();
    const classified = classifyCapability(message);
    const explicitCapability = input.capability ?? input.metadata?.capability;
    const capability = normalizeCapability(explicitCapability || classified.capability);

    return {
      message,
      capability,
      conversationId: input.conversationId ?? null,
      tenantId: input.tenantId ?? null,
      userId: input.userId ?? null,
      permissions: input.permissions ?? {},
      language: input.language ?? null,
      researchRequired: Boolean(input.researchRequired),
      channel: input.channel ?? 'web',
      metadata: input.metadata ?? {},
    };
  }
}
