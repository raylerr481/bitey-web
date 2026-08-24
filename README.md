# Bitey IA Web

`bitey-web` is the **general Bitey IA web application and the Cloudflare-hosted supracerebro of Bitey IA**.

It is the independent general-purpose Bitey IA product. `bitey-ia-app` is its Android/mobile client. Bitey Web is not a BiteFixes application and is not powered by `bitefixes-backend` as its general intelligence layer.

## Product architecture

```text
                       BITEY IA
                  General AI product
                          │
                 ┌────────┴────────┐
                 │                 │
            bitey-web        bitey-ia-app
           Supracerebro          Android
            Cloudflare           client
                 │                 │
                 └────────┬────────┘
                          │
                  shared Bitey IA
                    experience
                          │
              explicit authorized contracts
                          │
                     BiteFixes
                   enterprise use
```

### Hard boundary

**Bitey Web is the Bitey IA supracerebro.** `bitefixes-backend` is a separate specialized enterprise backend for BiteFixes.com. It must not be treated as the general brain of Bitey IA.

BiteFixes may consume Bitey IA capabilities through explicit, authorized enterprise contracts. BiteFixes company data, memory, services and workflows remain isolated and scoped to the BiteFixes enterprise system.

## Frontend direction

The web interface is minimal and AI-first, with a modern assistant-style experience without copying proprietary implementation or branding.

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

- Attachments/tools menu
- Files
- Images
- Data files
- Library files
- Microphone
- Message composer
- Conversation persistence

## Mobile

`bitey-ia-app` is the **Android/mobile client of this same Bitey IA product**. It communicates with Bitey Web/Cloudflare contracts and must not use BiteFixes Backend as its primary brain.

## BiteFixes relationship

BiteFixes is a separate company/product ecosystem:

```text
Bitey IA Web / App
       │
       │ authorized enterprise contract
       ▼
Bitey IA enterprise channel
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
- Production deployment through Cloudflare Workers Builds.

## Does not belong here

- BiteFixes-only business logic as the general brain.
- BiteFixes App implementation.
- BiteFixes Backend implementation.
- Private enterprise data without authorization.
- Provider secrets in browser code.

## Production and CI/CD

The Worker is connected to GitHub through Cloudflare Workers Builds. Production commits on the configured production branch are built and deployed through Wrangler. Cloudflare documents that a successful build using `npx wrangler deploy` creates a version and promotes it to the active deployment. citeturn0search0turn0search4

## Current priority

1. Keep Bitey Web minimal and reliable.
2. Make conversations persist per user.
3. Make projects, library, profile and settings real functions.
4. Keep web and Android behavior aligned.
5. Expand tools, memory, research and agents inside Bitey itself.
6. Connect BiteFixes only through explicit contextual enterprise contracts.
7. Validate the deployed Cloudflare Worker after every production change.
