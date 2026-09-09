# Bitey IA Web — General AI Web Channel

`bitey-web` is the official web channel of **Bitey IA**, the general/integral AI system. It provides the web interface for general intelligence, memory, planning, evaluation, tools, models, and policies. It is a channel, not a separate brain.

## Language and naming standard

All repository documentation, API contracts, backend/frontend references, variable names, model fields, JSON keys, configuration keys, database-facing names, endpoint parameters, and internal technical identifiers must use **English**.

The user interface may be localized, but technical identifiers must remain English and consistent across the Bitey ecosystem.

Examples: `job_id`, `company`, `location`, `modality`, `skills`, `match_score`, `application`, `VITE_JOBIA_API_URL`.

Do not introduce Spanish variable names, JSON keys, API parameters, database fields, or internal identifiers in new code.

## Module architecture

```text
                         BITEY IA
                    general intelligence
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

**JobIA is a specialized module of Bitey IA.** Its domain is employment and professional opportunities. `bitey-web` is only the web channel of Bitey IA and must not be treated as the parent backend or as a second intelligence system.

## Responsibilities of Bitey IA Web

The web channel presents and coordinates access to general Bitey IA capabilities. The underlying Bitey IA system remains authoritative for:

- general context and intent understanding;
- planning and task decomposition;
- memory and general knowledge;
- tool selection;
- model selection and routing;
- evaluation, contradiction detection, and confidence;
- permissions and risk policies;
- learning and observations;
- workspace and general capabilities.

Models are replaceable inference workers. Bitey IA must not depend on a single model provider.

## JobIA as a module

JobIA implements specialized employment intelligence through its own backend and versioned `jobia-v1` contract.

```text
Bitey IA
   │
   │ specialized employment capability
   ▼
 JobIA Backend
   │
   ├── opportunities
   ├── matching / ranking
   ├── profiles
   ├── applications
   └── alerts
   │
   ├───────────────┐
   ▼               ▼
JobIA-Web      JobIA-app
web channel    Android channel
```

The JobIA backend may request general Bitey IA capabilities when required. Client channels must never depend on private implementation details of either intelligence layer.

## Bitey Trainer

`bitey-trainer` is an internal Bitey IA capability for training, evaluation, and validation of specialized capabilities used by modules such as JobIA. It is not a client and not a second brain.

```text
Bitey Trainer → validates capabilities → JobIA → channels
```

## JobIA channels

- **JobIA-Web:** official web channel.
- **JobIA-app:** official Android channel.

Both consume the same JobIA backend contract. Neither contains private credentials or a parallel backend.

## Data and persistence

Supabase/Postgres is the canonical persistence layer when Bitey IA requires persistent application data. Modules must access data through appropriate contracts and isolation boundaries.

Neo4j and MongoDB are not architectural dependencies.

## Cost policy

The architecture is **free-first and no-surprise-cost**:

- Prefer free services, open-source software, or free tiers without automatic billing risk.
- Never add a provider that requires a payment card just to start or that can silently create charges for entry/egress, API requests, traffic, storage, or execution.
- **Railway is explicitly excluded** from BiteFixes/Bitey infrastructure.
- Cloudflare is allowed when its free usage is sufficient and any later cost occurs only after a clearly defined usage threshold; paid plans and automatic billing must never be enabled without explicit approval.
- Before incorporating a new service, verify pricing, billing behavior, limits, card requirements, and overage behavior.
- If a service can generate costs without an explicit decision first, use a safer alternative.
- This README policy is documentation-only and must not alter existing working runtime integrations.

Gemini API is not required.

## Security

- Secrets are server-side only.
- External models are untrusted inputs until evaluated.
- Tools require explicit permissions.
- Private context is isolated by user/tenant.
- High-impact actions require authorization.
- Modules communicate through versioned contracts.

## Principle

> **Bitey IA is the general system. `bitey-web` is its web channel. JobIA is a specialized employment/work module of Bitey IA. JobIA-Web and JobIA-app are JobIA channels. Bitey Trainer is an internal training and validation capability.**
