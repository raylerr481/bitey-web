# Bitey AI Web

`bitey-web` is the **main web application for Bitey AI**, developed and deployed on **Cloudflare**.

Its purpose is to provide the general-purpose Bitey AI experience through the web: conversation, context, memory, research, reasoning, tools, knowledge and agent orchestration.

## Product identity

**Public product:** Bitey AI  
**Architectural role:** independent general AI application and intelligence layer  
**Primary platform:** Cloudflare

The public interface should use **Bitey AI** as the product name. Internal architectural concepts should not be exposed as branding unless intentionally designed for users.

## Architectural boundary

```text
                         BITEY AI
                            │
                    ┌───────┴────────┐
                    │                │
                bitey-web        Cloudflare
                    │                │
                    └───────┬────────┘
                            │
                 Intelligence / orchestration
                 ├─ conversation + context
                 ├─ memory
                 ├─ research
                 ├─ reasoning
                 ├─ knowledge retrieval
                 ├─ tools
                 ├─ agents
                 └─ authorized enterprise capabilities
                            │
             AI providers / research / authorized data
```

Bitey AI is independent from `bitefixes-backend`. BiteFixes-specific business logic remains in the specialized BiteFixes system.

## Relationship with the mobile application

`bitey-ai-app` is the Android/mobile client for the same general Bitey AI product. It should consume the same authorized Bitey AI services and contracts rather than becoming an independent second AI.

```text
Bitey AI
├── bitey-web
│   └── Web application / Cloudflare
│
└── bitey-ai-app
    └── Android application
```

The web and mobile clients should share identity, conversation services, memory policies and authorized capabilities where the backend contracts support them.

## Relationship with enterprise systems

Bitey AI can interact with specialized enterprise systems through explicit, authorized contracts.

```text
Bitey AI
   │
   ├── Bitey AI Web (`bitey-web`)
   ├── Bitey AI App (`bitey-ai-app`)
   ├── WordPress Enterprise Plugin (`bitey-ai`)
   │
   └── authorized enterprise integrations
            └── BiteFixes Backend (`bitefixes-backend`)
```

Bitey AI does not automatically inherit private BiteFixes data. Company context, permissions, credentials and tenant boundaries remain controlled by the authorized enterprise backend.

## Core responsibilities

- Independent general AI experience and orchestration.
- Main Bitey AI web application.
- Conversation and context continuity.
- Intelligent web research.
- Reasoning and tool orchestration.
- Agent workflows.
- Memory and knowledge retrieval.
- Provider-neutral AI integration.
- Projects, conversations and library experience.
- Authorized enterprise AI integrations with strict tenant isolation.
- Cloudflare deployment, observability, security and controlled production evolution.

## What does NOT belong here

- BiteFixes-only business workflows as the general core.
- WordPress plugin implementation.
- BiteFixes mobile application implementation.
- Provider API secrets in browser code.
- A duplicate copy of the BiteFixes enterprise brain.
- Uncontrolled cross-tenant company memory.

## Ecosystem

| Repository | Product | Role |
|---|---|---|
| `bitey-web` | **Bitey AI Web** | Main general Bitey AI web application on Cloudflare |
| `bitey-ai-app` | **Bitey AI App** | General Bitey AI Android application |
| `bitey-ai` | **Bitey AI Enterprise WordPress Plugin** | Global WordPress enterprise channel |
| `bitefixes-backend` | **BiteFixes Backend** | Specialized BiteFixes enterprise intelligence/backend |
| `bitefixes-app` | **BiteFixes App** | BiteFixes mobile channel |

## Development priorities

1. Stable responsive dark UI and reliable chat.
2. Persistent user identity, conversations and messages.
3. Persistent projects and library.
4. Research engine with source/evidence handling.
5. Memory and knowledge retrieval.
6. Tool and agent orchestration.
7. Cloudflare-native intelligence services and integrations.
8. Shared web/mobile contracts for Bitey AI.
9. Security, observability and controlled production deployment.

## Engineering rules

1. Keep Bitey AI independent from any single provider.
2. Separate intelligence, UI, persistence and external services.
3. Treat memory as explicit, scoped and authorized.
4. Preserve tenant isolation for enterprise context.
5. Never place private API credentials in client-side code.
6. Do not claim a capability until it is implemented and tested.
7. Prefer incremental evolution over duplicated engines.
8. Integrate specialized enterprise systems through explicit contracts.
9. Validate production behavior after Cloudflare deployment, not only source code.
10. Keep web and mobile clients aligned around the same authorized Bitey AI product contracts.

## Development and deployment

The production evolution of `bitey-web` is associated with the Bitey Web Cloudflare Worker. Cloudflare is the primary infrastructure platform for developing, deploying and evolving Bitey AI Web.
