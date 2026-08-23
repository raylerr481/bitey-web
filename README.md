# Bitey IA

`bitey-web` is the foundation of **Bitey IA**, the complete web-based **supracerebro** of the Bitey ecosystem. It is intended to provide a full AI experience comparable in interaction model to ChatGPT or Claude, while remaining provider-neutral and capable of general and enterprise AI contexts.

> **Boundary:** Bitey IA is a separate project from `bitefixes-backend`. It does not replace, merge with, or modify the BiteFixes enterprise brain.

## Supracerebro mission

Bitey IA is the reusable intelligence foundation for:

- natural conversation;
- context understanding and continuity;
- explicit memory boundaries;
- intelligent web research;
- reasoning and orchestration;
- external AI provider collaboration;
- tools and capabilities;
- enterprise/company context when explicitly authorized;
- future Bitey products and channels.

The foundation separates intelligence orchestration from providers, persistence, search vendors and business-specific implementations.

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
  ├─ enterprise context boundary
  ├─ provider-neutral reasoning
  └─ tool boundary
  ↓
AI providers / research providers / authorized data sources
```

The foundation lives under `src/core/`. It is an extensible orchestration base, not a claim that every intelligence capability is already production-complete.

## Enterprise AI model

Bitey IA can apply the enterprise model developed and validated through BiteFixes without copying BiteFixes-specific business logic into this repository:

```text
Bitey IA
  ↓
Authorized enterprise context
  ↓
Company AI Profile
  ↓
Knowledge + memory + permissions
  ↓
Research + reasoning
  ↓
Coherent answer / action
```

Tenant isolation and authorization are mandatory. A company's private context must never become context for another company.

## Ecosystem boundaries

- `bitey-web` — **Bitey IA**, the web supracerebro and complete ChatGPT/Claude-like AI experience.
- `bitey-ai` — **Bitey Plugin Web**, the WordPress plugin/channel installed on sites such as BiteFixes.com.
- `bitefixes-backend` — **BiteFixes enterprise brain/backend**, specialized for BiteFixes.com, its business context and authorized channels such as the website widget, WhatsApp and Telegram. It remains independent.
- `bitefixes-app` — **BiteFixes App**, the mobile extension/application of BiteFixes.com. It is a channel/client, not another brain.

## Naming

| Repository | Product name | Role |
| --- | --- | --- |
| `bitey-web` | **Bitey IA** | Supracerebro + web AI experience |
| `bitey-ai` | **Bitey Plugin Web** | WordPress plugin/channel |
| `bitefixes-backend` | **BiteFixes Backend** | BiteFixes enterprise brain |
| `bitefixes-app` | **BiteFixes App** | Mobile extension of BiteFixes.com |

Repository slugs are kept stable where a repository-level rename operation is unavailable through the connected GitHub interface. No duplicate repository is created for a naming change.
