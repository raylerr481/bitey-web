# Bitey IA Web — Central Cognitive Brain

`bitey-web` is the **central cognitive brain of Bitey IA**. It is the general/integral intelligence layer that coordinates general context, reasoning, memory access, planning, tools, models, evaluation, policies, and specialized capabilities across the Bitey ecosystem.

It is not merely a web channel and it is not a second independent intelligence system.

## Central architecture

The Bitey ecosystem uses **one shared Supabase/Postgres instance for canonical memory and data persistence**:

- Supabase project: **`bitefixes-backed`**
- The shared persistence layer is used by the central Bitey IA architecture and the specialized BiteFixes enterprise AI.
- Separate application repositories do not create parallel Supabase memory systems for the same ecosystem.

```text
                         BITEY IA ECOSYSTEM
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
          Bitey IA Web / GitHub        BiteFixes Backend / GitHub
          CENTRAL COGNITIVE BRAIN      SPECIALIZED ENTERPRISE AI
                    │                           │
                    └─────────────┬─────────────┘
                                  │
                         shared contracts
                                  │
                                  ▼
                     Supabase/Postgres
                       `bitefixes-backed`
                     single shared memory/data
```

### Responsibilities

**Bitey IA Web** is responsible for the general cognitive layer, including:

- general context and intent understanding;
- reasoning and planning;
- task decomposition and orchestration;
- general memory and knowledge access;
- tool selection and coordination;
- model selection and routing;
- evaluation, contradiction detection, and confidence;
- permissions and risk policies;
- learning and observations;
- coordination of specialized modules.

**BiteFixes Backend** remains the specialized enterprise implementation for BiteFixes. It owns the BiteFixes business/API domain and provides contextual enterprise AI capabilities through explicit contracts with the central Bitey IA layer.

The two systems have different responsibilities but share the same canonical Supabase memory/data architecture.

## Language and naming standard

All repository documentation, API contracts, backend/frontend references, variable names, model fields, JSON keys, configuration keys, database-facing names, endpoint parameters, and internal technical identifiers must use **English**.

The user interface may be localized, but technical identifiers must remain English and consistent across the Bitey ecosystem.

Examples: `job_id`, `company`, `location`, `modality`, `skills`, `match_score`, `application`, `VITE_JOBIA_API_URL`.

Do not introduce Spanish variable names, JSON keys, API parameters, database fields, or internal identifiers in new code.

## Specialized modules

```text
                         Bitey IA
                  central cognitive brain
                           │
             ┌─────────────┼─────────────┐
             │             │             │
          JobIA         Bitey SBT     other modules
       employment/work     trading
             │
             ▼
       JobIA Backend
             │
       ┌─────┴─────┐
       ▼           ▼
  JobIA-Web    JobIA-app
  web channel  Android channel
```

**JobIA is a specialized module of Bitey IA.** Its domain is employment and professional opportunities. Client channels must consume explicit contracts and must not become alternative brains.

## Bitey Trainer

`bitey-trainer` is an internal Bitey IA capability for training, evaluation, and validation of specialized capabilities used by modules such as JobIA. It is not a client and not a second brain.

```text
Bitey Trainer → validates capabilities → specialized modules → channels
```

## Data and persistence

**`bitefixes-backed` is the single canonical Supabase/Postgres persistence and memory instance for the Bitey/BiteFixes architecture.**

The shared instance provides the canonical data foundation while application responsibilities remain separated by repository and API contract.

Neo4j and MongoDB are not architectural dependencies.

A new module must not create another Supabase memory instance merely to duplicate ecosystem state.

## BiteFixes boundary

BiteFixes remains an enterprise domain with its own business rules, CRM, SaaS and operational APIs. The specialized BiteFixes AI implementation remains in `bitefixes-backend`.

The central Bitey IA brain may coordinate with BiteFixes Backend through explicit contracts, but general Bitey IA must not absorb or replace the BiteFixes business domain.

## Security

- Secrets are server-side only.
- External models are untrusted inputs until evaluated.
- Tools require explicit permissions.
- Private context is isolated by user/tenant.
- High-impact actions require authorization.
- Modules communicate through versioned contracts.
- Shared persistence must preserve tenant and domain isolation.
- No service-role or privileged database credentials belong in browser code.

## Cost policy

The architecture is **free-first and no-surprise-cost**:

- Prefer free services, open-source software, or free tiers without automatic billing risk.
- Never add a provider that requires a payment card just to start or that can silently create charges for entry/egress, API requests, traffic, storage, or execution.
- **Railway is explicitly excluded** from BiteFixes/Bitey infrastructure.
- Cloudflare is allowed when its free usage is sufficient and any later cost occurs only after a clearly defined usage threshold; paid plans and automatic billing must never be enabled without explicit approval.
- Before incorporating a new service, verify pricing, billing behavior, limits, card requirements, and overage behavior.
- If a service can generate costs without an explicit decision first, use a safer alternative.

Gemini API is not required.

## Principle

> **Bitey IA Web is the central cognitive brain. BiteFixes Backend is the specialized BiteFixes enterprise AI/business backend. Both integrate with the same canonical Supabase memory/data instance, `bitefixes-backed`. Specialized modules remain separated by explicit contracts and must not create parallel ecosystem memory systems.**
