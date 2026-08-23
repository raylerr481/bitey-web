# Bitey Web

`bitey-web` is the public web facade for **Bitey**, designed as a ChatGPT-like web experience dedicated to the Bitey AI platform.

It is a **channel/interface**, not an independent intelligence engine.

## Architecture

```text
User
  ↓
bitey-web
  ↓
Bitey Backend
  ↓
Company AI Profile + authorized context
  ↓
Bitey IA
  ├─ knowledge / memory
  ├─ intelligent web research
  ├─ service/workflow reasoning
  └─ external AI collaboration when useful
  ↓
response
  ↓
bitey-web
```

The backend is the single source of truth for intelligence, context, memory, research, business rules, tenant isolation and evolution. The web facade should not create a second AI brain or store provider credentials in browser code.

## Product role

Bitey Web provides a dedicated public place where users can interact with Bitey directly, similar in interaction style to a general AI chat application while remaining grounded in Bitey's platform architecture.

The experience should feel simple to the user. Internal concepts such as Company AI Profile construction, provider routing and evaluation/evolution should remain server-side unless intentionally exposed as product functionality.

## Platform repositories

- `bitefixes-backend` — authoritative Bitey IA and intelligence core.
- `bitey-web` — this public web facade.
- `bitey-ai` — WordPress channel/plugin.
- `bitefixes-app` — mobile channel for BiteFixes and Bitey.
