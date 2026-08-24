# Bitey IA

`bitey-web` is the **general Bitey IA web application and intelligence foundation**.

It provides the main user-facing AI experience and is designed to evolve into a provider-neutral, context-aware AI platform with conversation, memory, research, tools and enterprise capabilities.

> **Important boundary:** Bitey IA is independent from the specialized `bitefixes-backend`. It must not absorb BiteFixes-specific business logic.

## Role

```text
User
 ↓
Bitey IA Web
 ↓
Bitey intelligence/orchestration
 ├─ context
 ├─ conversation
 ├─ memory boundaries
 ├─ research
 ├─ tools
 ├─ reasoning
 └─ authorized enterprise context
 ↓
AI providers / research services / authorized data sources
```

## Product responsibilities

- General AI conversation experience.
- Context and conversation continuity.
- Intelligent web research.
- Tool orchestration.
- Provider-neutral AI integration.
- User/project/library experience.
- Future persistent memory and knowledge retrieval.
- Authorized enterprise AI experiences without leaking tenant data.

## What it is NOT

- It is not the BiteFixes business backend.
- It is not the WordPress plugin.
- It is not the BiteFixes mobile application.
- It must not contain BiteFixes-only workflows as its core architecture.

## Repository ecosystem

| Repository | Product | Role |
|---|---|---|
| `bitey-web` | **Bitey IA** | General web AI experience + intelligence foundation |
| `bitey-ai` | **Bitey AI Enterprise Plugin** | WordPress enterprise channel |
| `bitefixes-backend` | **BiteFixes Backend** | Specialized BiteFixes enterprise backend/brain |
| `bitefixes-app` | **BiteFixes App** | BiteFixes mobile channel |

## Design principles

1. Keep the web experience independent from any single AI provider.
2. Prefer orchestration and tool selection over hard-coded provider logic.
3. Treat memory as explicit, authorized and scoped data.
4. Treat company context as tenant-isolated data.
5. Keep private credentials out of the browser.
6. Research current information when freshness is required and preserve evidence boundaries.
7. Do not claim capabilities that are not actually implemented.
8. Keep UI, intelligence, persistence and external services separable.

## Development direction

Priority order:

1. Stable chat and responsive dark UI.
2. Persistent conversations and user identity.
3. Project and library persistence.
4. Research engine with evidence/source handling.
5. Memory and knowledge retrieval.
6. Tool/agent orchestration.
7. Production observability, security and deployment controls.

The term **Bitey IA** is the public product identity. Internal architectural terminology may describe intelligence/orchestration components, but public UI should not expose obsolete product names.
