# Bitey IA Web

`bitey-web` is the **independent general-purpose Bitey IA product** and its primary Cloudflare web application.

## Architecture

```text
                    BITEY IA
                 Independent brain
                       │
              ┌────────┴────────┐
              │                 │
         bitey-web         bitey-ia-app
          Cloudflare          Android
              │                 │
              └────────┬────────┘
                       │
              same Bitey IA product
                       │
              authorized integrations
                       │
                 BiteFixes only
              enterprise context
```

### Hard boundary

**Bitey Web is NOT powered by `bitefixes-backend`.** The Bitey Web/Cloudflare platform remains the independent intelligence layer. `bitefixes-backend` is only the operational backend for the BiteFixes enterprise system.

BiteFixes can consume Bitey through an explicit enterprise integration, but BiteFixes data must never become the general brain of Bitey without authorization and tenant isolation.

## Frontend direction

The web interface is intentionally minimal and AI-first, inspired by modern AI assistant usability without copying proprietary implementation or branding.

Primary navigation:

- New conversation
- Search
- Projects
- Library
- Explore AI
- Conversation history
- Settings
- Help
- User profile

Chat actions:

- `+` attachments/tools menu
- Files
- Images
- Data files
- Library files
- Microphone
- Message composer
- Conversation persistence

The home screen remains uncluttered: one central conversation area, a compact sidebar and a focused composer.

## Mobile

`bitey-ia-app` is the Android/mobile client of this same general Bitey IA product. It communicates with Bitey Web/Cloudflare contracts, not with BiteFixes Backend as its primary brain.

## BiteFixes relationship

BiteFixes is a separate company/product ecosystem. Its specialized assistant is **Bitey IA Empresarial**, contextualized for BiteFixes services, customers, CRM, tickets, quotations and business workflows.

```text
Bitey IA Web / App
       │
       │ authorized enterprise context
       ▼
Bitey IA Empresarial
       │
       ▼
BiteFixes Backend
```

This integration is contextualized and scoped. It does not redefine Bitey IA's general identity or architecture.

## Responsibilities

- Bitey IA web UI and general AI conversation experience.
- User profile, conversation history, projects and library UX.
- Files, images, data and voice interaction UX.
- Cloudflare-native Bitey IA services.
- Shared product contracts with Bitey IA App.
- Authorized enterprise integrations.

## Does not belong here

- BiteFixes-only business logic as the general brain.
- BiteFixes App implementation.
- BiteFixes Backend implementation.
- Private enterprise data without authorization.
- Provider secrets in browser code.

## Current priority

1. Keep Bitey Web minimal and reliable.
2. Make conversations persist per user.
3. Build projects/library/profile/settings as real functions.
4. Keep web and Android behavior aligned.
5. Expand tools, memory, research and agents inside Bitey itself.
6. Connect BiteFixes only through explicit contextual enterprise contracts.
7. Validate the deployed Cloudflare Worker after each production change.
