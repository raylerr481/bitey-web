/**
 * Enterprise context boundary for Bitey IA.
 *
 * Keeps company-specific context explicit and isolated from the general
 * supracerebro. Bitey IA can consume an authorized Company AI Profile without
 * embedding BiteFixes-specific business rules in this repository.
 */
export class EnterpriseContext {
  constructor({ profileProvider = null, knowledgeProvider = null } = {}) {
    this.profileProvider = profileProvider;
    this.knowledgeProvider = knowledgeProvider;
  }

  async resolve({ tenantId = null, userId = null, permissions = {} } = {}) {
    if (!tenantId || permissions.enterpriseContext !== true) {
      return { enabled: false, tenantId: null, profile: null, knowledge: [] };
    }

    const profile = await this.profileProvider?.get?.(tenantId, userId) ?? null;
    const knowledge = await this.knowledgeProvider?.search?.(tenantId) ?? [];

    return { enabled: true, tenantId, profile, knowledge };
  }
}
