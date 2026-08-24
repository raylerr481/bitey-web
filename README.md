# Bitey IA — Independent AI Supracerebro

`bitey-web` is **Bitey IA**, an independent AI suprabrain (supracerebro) being developed and evolved on **Cloudflare**.

It is the main general-purpose AI system of the Bitey ecosystem. Its purpose is to evolve beyond a conventional chatbot into a context-aware intelligence platform with conversation, memory, research, reasoning, tools, knowledge and agent orchestration.

## Product identity

**Public product:** Bitey IA  
**Architectural role:** Independent AI supracerebro  
**Primary platform:** Cloudflare

The term **supracerebro** describes the architectural role of Bitey IA. Public UI should use the product name **Bitey IA** and should not expose obsolete branding or internal implementation labels unless intentionally designed for users.

## Architectural boundary

```text
                         BITEY IA
                 Independent AI Supracerebro
                              │
                    ┌─────────┴─────────┐
                    │                   │
                bitey-web           Cloudflare
                    │                   │
                    └─────────┬─────────┘
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

Bitey IA is **independent from `bitefixes-backend`**. BiteFixes-specific business logic must remain in the specialized BiteFixes system.

## Relationship with enterprise systems

Bitey IA can interact with specialized enterprise systems through explicit, authorized contracts.

```text
Bitey IA — independent supracerebro
          │
          ├── authorized enterprise integrations
          │
          └── BiteFixes Backend when explicitly authorized
                         │
                         └── BiteFixes enterprise intelligence
```

Bitey IA does not automatically inherit private BiteFixes data. Company context, permissions, credentials and tenant boundaries remain controlled by the authorized enterprise backend.

## Core responsibilities

- Independent general AI intelligence and orchestration.
- Main Bitey IA web experience.
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
| `bitey-web` | **Bitey IA** | Independent AI supracerebro developed on Cloudflare |
| `bitey-ai` | **Bitey AI Enterprise WordPress Plugin** | Global WordPress enterprise channel/integration |
| `bitefixes-backend` | **BiteFixes Backend** | Specialized BiteFixes enterprise backend/brain |
| `bitefixes-app` | **BiteFixes App** | BiteFixes mobile channel |

## Development priorities

1. Stable responsive dark UI and reliable chat.
2. Persistent user identity, conversations and messages.
3. Persistent projects and library.
4. Research engine with source/evidence handling.
5. Memory and knowledge retrieval.
6. Tool and agent orchestration.
7. Cloudflare-native intelligence services and integrations.
8. Security, observability and controlled production deployment.

## Engineering rules

1. Keep the supracerebro independent from any single provider.
2. Separate intelligence, UI, persistence and external services.
3. Treat memory as explicit, scoped and authorized.
4. Preserve tenant isolation for enterprise context.
5. Never place private API credentials in client-side code.
6. Do not claim a capability until it is implemented and tested.
7. Prefer incremental evolution over duplicated engines.
8. Integrate specialized enterprise brains through explicit contracts.
9. Validate production behavior after Cloudflare deployment, not only source code.
10. Preserve Bitey IA as an independent product and architectural authority for the general AI layer.

## Development and deployment

The production evolution of `bitey-web` is associated with the Bitey Web Cloudflare Worker. Cloudflare is the primary infrastructure platform for developing, deploying and evolving the independent Bitey IA supracerebro.
