# Bitey IA Web — Central Cognitive Brain

`bitey-web` is the **central cognitive brain of Bitey IA**. It is the general/integral intelligence layer that coordinates general context, reasoning, memory access, planning, tools, models, evaluation, policies, and specialized capabilities across the Bitey ecosystem.

It is not merely a web channel and it is not a second independent intelligence system.

## Central architecture

The Bitey ecosystem uses **two separate Supabase/Postgres projects with explicit ownership boundaries**:

- **Bitey IA Web** uses its own project, **`bitey-ia`**, for general conversation memory, cognition, learning, and Bitey IA modules.
- **BiteFixes Backend** keeps its business data and existing structure in **`bitefixes-backed`**.
- The projects remain separate. Bitey IA may call BiteFixes through authorized API contracts, but it must not write to, migrate, or absorb BiteFixes tables.

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
             ┌─────────────────────┐     ┌─────────────────────┐
             │ Supabase/Postgres   │     │ Supabase/Postgres   │
             │ `bitey-ia`          │     │ `bitefixes-backed`  │
             │ Bitey IA data       │     │ BiteFixes data      │
             └─────────────────────┘     └─────────────────────┘
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

**The two Supabase projects remain independent.** `bitey-ia` is the persistence target for Bitey IA Web and its general cognitive memory. `bitefixes-backed` is the persistence target for BiteFixes Backend and its existing business domain. Do not merge their schemas or data, and do not redirect Bitey IA memory writes into `bitefixes-backed`.

Neo4j and MongoDB are not architectural dependencies. A module must use its assigned project and explicit API contracts rather than duplicating or crossing domain-owned data.

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

> **Bitey IA Web is the central cognitive brain and uses `bitey-ia`. BiteFixes Backend is the specialized BiteFixes enterprise AI/business backend and keeps `bitefixes-backed`. The databases remain separate; integration occurs only through authorized, explicit contracts.**


## ChatGPT-style interaction layer

The web channel exposes a unified API under `/api/v2`:

- `GET /api/v2/capabilities` — capability discovery for the client.
- `POST /api/v2/chat` — multi-turn conversational orchestration.
- Automatic routing between normal chat, public-web research, deterministic mathematics, and code-analysis mode.
- Verified-source collection with explicit source metadata returned to the frontend.
- Deterministic arithmetic/statistical calculations are kept outside the language model.
- Provider failover remains behind `ProviderGateway`; external models are inference workers, not system authorities.
- Public answers are sanitized and evaluated before being persisted.
- The legacy `/api/v1` cognitive pipeline remains available for compatibility and specialized endpoints.

The intended execution flow is:

```text
User message
   │
   ▼
Intent + cognitive state
   │
   ├── mathematics ──► deterministic math engine
   │
   ├── freshness/research ──► web research ──► fetch/verify/contrast
   │
   ├── module domain ──► explicit specialized contract
   │
   └── general task
          │
          ▼
     provider gateway
          │
          ▼
   executive evaluation
          │
          ▼
      public answer
```

Bitey must never treat a model's generated text as evidence. Current information comes from tools and retrieved sources; mathematical results come from deterministic functions; specialized modules remain bounded by explicit contracts.

### Engineering guardrails

- Keep technical identifiers in English.
- Keep secrets and privileged Supabase credentials server-side.
- Do not expose chain-of-thought or hidden model reasoning.
- Do not enable arbitrary code execution by default.
- Do not execute trading orders from Bitey IA Web.
- Keep Qwen and Gemini out of the active free-provider routing policy.
- Preserve the free-first/no-surprise-cost policy.


## Free inference server pool

Bitey IA supports multiple Ollama workers without making any one VPS mandatory. The local GPU Ollama worker remains the preferred inference host; optional free-tier/user-owned VPS Ollama workers are added through configuration.

Execution order: Local Ollama -> Ollama VPS #1 -> Ollama VPS #2 -> free OpenRouter/Groq/Hugging Face routes -> Bitey Native.

Configure remote workers with OLLAMA_REMOTE_ENABLED=true and OLLAMA_REMOTE_URLS=https://server-1.example.com,https://server-2.example.com.

Each remote endpoint must expose the standard Ollama API (/api/tags and /api/chat). Bitey health-checks each worker and automatically skips unavailable workers. Remote workers are inference workers only and are never treated as evidence sources.

The pool is provider-agnostic so free infrastructure can be changed without modifying the cognitive architecture. Oracle Cloud Always Free is one deployment target; other providers can be added by exposing the same Ollama API. Free-tier availability and limits must be verified before provisioning.


## Cloudflare Workers AI free route

Bitey IA can optionally use Cloudflare Workers AI as a free inference worker. Cloudflare currently provides a daily free Workers AI allocation measured in Neurons; this is separate from the Workers Free request quota. Bitey keeps this route opt-in and free-only.

Enable with:
- `CLOUDFLARE_AI_FREE_ENABLED=true`
- `CLOUDFLARE_ACCOUNT_ID=<account-id>`
- `CLOUDFLARE_API_TOKEN=<server-side-token>`
- `CLOUDFLARE_AI_FREE_MODEL=@cf/zai-org/glm-4.7-flash`

The free-only allowlist currently includes `@cf/zai-org/glm-4.7-flash`, `@cf/google/gemma-4-26b-a4b-it`, and `@cf/nvidia/nemotron-3-120b`. If the provider returns a free-limit/model-unavailable response, Bitey automatically fails over to the next eligible provider. Cloudflare credentials remain server-side.

This route does not enable a paid Cloudflare plan and does not treat the 100,000/day Workers request quota as 100,000 free AI inferences.