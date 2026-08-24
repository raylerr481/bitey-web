# Bitey IA

`bitey-web` is the **general Bitey IA web application and intelligence foundation**.

It is the main user-facing AI experience for the Bitey ecosystem: a provider-neutral, context-aware AI platform designed to evolve with conversation, memory, research, tools, reasoning and authorized enterprise capabilities.

## Product identity

**Public product:** Bitey IA

Internal architecture may use terms such as intelligence engine, orchestration, memory engine or reasoning engine. The public interface must not expose obsolete product names.

## Architectural boundary

```text
User
  ↓
Bitey IA Web
  ↓
Bitey intelligence / orchestration
  ├─ conversation + context
  ├─ memory boundaries
  ├─ research
  ├─ reasoning
  ├─ tools
  └─ authorized enterprise context
  ↓
AI providers / research services / authorized data sources
```

`bitey-web` is independent from `bitefixes-backend`. It must not absorb BiteFixes-specific business logic merely because both projects share architectural patterns.

## Core responsibilities

- Main Bitey IA web experience.
- Conversation and context continuity.
- Intelligent web research.
- Reasoning and tool orchestration.
- Provider-neutral AI integration.
- Projects, conversations and library UX.
- Persistent memory and knowledge retrieval as they are implemented.
- Authorized enterprise AI experiences with strict tenant isolation.
- Production observability, security and deployment controls.

## What does NOT belong here

- BiteFixes-only business workflows as the general core.
- WordPress plugin code.
- BiteFixes mobile application code.
- Provider API secrets in browser code.
- Another independent copy of the BiteFixes enterprise brain.

## Ecosystem

| Repository | Product | Role |
|---|---|---|
| `bitey-web` | **Bitey IA** | General web AI experience + intelligence foundation |
| `bitey-ai` | **Bitey AI Enterprise WordPress Plugin** | Global WordPress enterprise channel/integration |
| `bitefixes-backend` | **BiteFixes Backend** | Specialized BiteFixes enterprise backend/brain |
| `bitefixes-app` | **BiteFixes App** | BiteFixes mobile channel |

## Enterprise relationship

Bitey IA can use an authorized company context when explicitly configured. Company data must remain tenant-scoped and permission-controlled.

```text
Bitey IA
   ↓
authorized enterprise context
   ↓
Company AI Profile / knowledge / permissions
   ↓
research + reasoning + tools
   ↓
response or authorized action
```

Bitey IA does not automatically inherit private BiteFixes data. Integration must occur through explicit contracts and authorization.

## Development priorities

1. Stable responsive dark UI and reliable chat.
2. Persistent user identity, conversations and messages.
3. Persistent projects and library.
4. Research engine with source/evidence handling.
5. Memory and knowledge retrieval.
6. Tool and agent orchestration.
7. Security, observability and controlled production deployment.

## Engineering rules

1. Keep intelligence separate from UI, persistence and external providers.
2. Keep provider-neutral interfaces wherever practical.
3. Treat memory as explicit, scoped and authorized.
4. Preserve tenant isolation for enterprise context.
5. Never place private API credentials in client-side code.
6. Do not claim a capability until it is implemented and tested.
7. Prefer incremental changes over duplicated engines.
8. Keep compatibility with the authorized backend contracts.
9. Validate production behavior after deployment, not only source code.

## Development

Use the repository's existing build/test instructions and validate the application locally before deployment. Production deployment is currently associated with the Bitey Web Cloudflare Worker.
