# Bitey IA

`bitey-web` is the foundation of **Bitey IA**, the complete web-based Bitey intelligence platform. It is intended to become the **supracerebro** of Bitey: a full AI experience comparable in interaction model to ChatGPT or Claude, while remaining provider-neutral and capable of supporting general and enterprise AI contexts.

> Important: this project is independent from `bitefixes-backend`. The BiteFixes backend remains the specialized brain/infrastructure for BiteFixes.com and its authorized channels. It is not being replaced, merged, or modified by this project.

## Supracerebro mission

Bitey IA is designed to provide the reusable intelligence foundation for:

- natural conversation;
- context understanding and continuity;
- memory through explicit adapters;
- intelligent web research;
- reasoning and orchestration;
- external AI provider collaboration;
- tools and capabilities;
- enterprise/company context when a tenant enables it;
- future Bitey products and channels.

The foundation deliberately separates intelligence orchestration from providers, persistence, web-search vendors and business-specific implementations.

## Current foundation

```text
User
  ↓
Bitey IA Web Experience
  ↓
Bitey Supracerebro
  ├─ request normalization
  ├─ context engine
  ├─ memory boundary
  ├─ web research boundary
  ├─ provider-neutral reasoning
  └─ tool boundary
  ↓
AI providers / research providers / authorized data sources
```

The initial foundation lives under `src/core/`. It is an orchestration boundary, not yet a claim that every intelligence capability is production-complete.

## Enterprise AI model

Bitey IA can later apply the enterprise model proven in BiteFixes without copying BiteFixes-specific business logic into this repository:

```text
Bitey IA
  ↓
Enterprise context
  ↓
Company AI Profile
  ↓
Knowledge + memory + permissions
  ↓
Research + reasoning
  ↓
Coherent answer / action
```

The enterprise layer must remain tenant-aware and must never leak one company's private context into another company.

## Repository boundaries

- `bitey-web` — **Bitey IA**, the web supracerebro foundation and web experience.
- `bitey-ai` — **Bitey Plugin Web**, the WordPress plugin/channel installed on sites such as BiteFixes.com.
- `bitefixes-backend` — specialized BiteFixes infrastructure and AI brain. It remains independent and is not merged into Bitey IA.
- `bitefixes-app` — BiteFixes application/extension and remains separate from the Bitey IA supracerebro.

## Naming transition

The intended product names are:

| Current repository | Intended product name |
| --- | --- |
| `bitey-web` | **Bitey IA** |
| `bitey-ai` | **Bitey Plugin Web** |
| `bitefixes-backend` | **BiteFixes Backend** |
| `bitefixes-app` | **BiteFixes App** |

The GitHub repository slugs require a repository-level rename operation; until that operation is available, the existing slugs remain stable so no repository is duplicated or lost.
