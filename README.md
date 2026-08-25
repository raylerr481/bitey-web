# Bitey IA Web

`bitey-web` is the **general Bitey IA web application and Cloudflare-hosted supracerebro** of the Bitey IA product.

## Objective

Provide a reliable, general-purpose AI experience through the web while keeping identity, conversations, memory, projects, files and settings scoped to each authenticated user.

**Bitey Web is the general Bitey IA product. It is not the BiteFixes business backend.**

## Product architecture

```text
                         BITEY IA
                    General AI product
                           │
              ┌────────────┴────────────┐
              │                         │
         Bitey Web                 Bitey IA App
         Cloudflare                  Android client
         supracerebro                     │
              │                           │
              └───────────┬───────────────┘
                          │
                    Supabase Auth
                          │
                 user-scoped data
                          │
        conversations / memory / projects / library

       authorized enterprise integrations
                          │
                          ▼
                    BiteFixes ecosystem
```

## Core functionalities

- AI-first chat and conversation management.
- New conversations and persistent history.
- User registration, authentication and session management through Supabase Auth.
- User-scoped conversations, messages and memory with authorization/RLS.
- User profile, settings and personalization.
- Projects and library experiences.
- File, image and data-file interaction where supported.
- Voice/microphone interaction where supported by the client.
- Search/research and future agent/tool capabilities through authorized server-side services.
- Cloudflare Worker runtime and production deployment through Cloudflare Workers Builds.
- Shared API contracts for the Bitey IA Android application.

## User identity and data boundary

```text
Authenticated user
        ↓
Supabase Auth identity
        ↓
user-scoped authorization
        ↓
conversations / messages / memory / projects / settings
```

A user must only access their own private data. Server-side authorization and Supabase RLS are authoritative; browser state is never treated as a security boundary.

## Hard architectural boundary

**Bitey Web is the Bitey IA supracerebro.** `bitefixes-backend` is a separate specialized enterprise backend for BiteFixes.com.

BiteFixes can consume Bitey IA capabilities through explicit, authorized contracts. BiteFixes customers, company knowledge, services, tickets, workflows and enterprise memory remain isolated within the BiteFixes ecosystem.

## Mobile relationship

`bitey-ia-app` is the Android/mobile client of this same Bitey IA product. It should authenticate users and communicate through the authorized Bitey IA contracts rather than treating `bitefixes-backend` as its general intelligence layer.

## Enterprise relationship

`bitey-ai` is the authorized enterprise WordPress channel for Bitey IA. It is an integration layer, not a duplicate supracerebro.

## Internal training infrastructure

Bitey may have internal training/evaluation components used to improve and evaluate Bitey against different AI systems. Such components are **internal infrastructure, not public product navigation or advertising**. External model use must respect each provider's API, licensing and usage terms.

## Responsibilities

- General Bitey IA web UX.
- Authentication/session UX and user profile.
- Conversation, memory, project and library UX.
- Files, images, data and voice interaction UX.
- Cloudflare-native server-side services.
- Authorized integrations and API contracts.
- Security boundaries and user-scoped persistence.
- Production deployment and operational validation.

## Does not belong here

- BiteFixes-only business logic as the general brain.
- BiteFixes App implementation.
- BiteFixes Backend implementation.
- Private enterprise data without authorization.
- AI provider secrets in browser code.
- Public links or marketing for internal training infrastructure.

## Ecosystem

| Repository | Product | Objective |
|---|---|---|
| `bitey-web` | **Bitey IA Web** | General Bitey IA web application and Cloudflare supracerebro |
| `bitey-ia-app` | **Bitey IA App** | Android/mobile client for the same Bitey IA product |
| `bitey-ai` | **Bitey IA Enterprise WordPress Plugin** | Authorized WordPress enterprise channel |
| `bitefixes-backend` | **BiteFixes Backend** | Specialized BiteFixes enterprise intelligence and API layer |
| `bitefixes-web` | **BiteFixes Web** | BiteFixes.com website/frontend |
| `bitefixes-app` | **BiteFixes App** | BiteFixes mobile customer/business channel |

## Production and CI/CD

The production Worker is connected to GitHub through Cloudflare Workers Builds. Changes must be validated before release, with particular attention to authentication, API contracts, RLS behavior and UI regressions.

## Current priorities

1. Keep Bitey Web reliable and AI-first.
2. Complete real user authentication and profile behavior.
3. Ensure conversations and memory remain isolated per user.
4. Align web and Android behavior.
5. Make projects, library and settings real functions.
6. Expand tools, research, memory and agents inside Bitey itself.
7. Keep enterprise integrations explicit and isolated.
8. Never expose internal training infrastructure as public navigation.
