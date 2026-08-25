# Bitey IA Web

`bitey-web` is the **general Bitey IA web application and Cloudflare-hosted supracerebro** of the Bitey IA product.

## Objective

Provide a reliable general-purpose AI experience through the web while keeping identity, conversations, memory, projects, files and settings scoped to each authenticated user.

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

                  Internal Bitey capability
                          │
                          ▼
                   Bitey Trainer
                 private/underground
                          │
          authorized external AI systems
                          │
                          ▼
              evaluation / training / offers
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

## Bitey Trainer — internal Bitey IA functionality

`bitey-trainer` is a **subordinate internal capability of Bitey IA Web**, not a separate public product.

Its objective is to identify and develop legitimate commercial opportunities in which external AI providers or AI companies contract for AI evaluation, training, benchmarking, red-teaming, quality assessment or other permitted model-improvement work involving Bitey IA and its infrastructure.

The intended operating model is:

```text
Bitey IA Web
     │
     ├── identifies an authorized training/evaluation opportunity
     │
     ▼
Bitey Trainer (internal)
     │
     ├── discovers/records eligible AI providers and contracts
     ├── evaluates provider requirements and permitted workloads
     ├── orchestrates approved external AI interactions
     ├── measures quality, cost, latency and task performance
     └── reports opportunities/results back to Bitey IA
```

Bitey Trainer must use the same **authorized external-AI integration pattern established by Bitey IA Web**. It must not bypass provider authentication, rate limits, licensing, usage restrictions or contractual requirements.

### Commercial objective

The Trainer is intended to help Bitey IA find legitimate paid opportunities where an AI company/provider pays for services such as:

- model evaluation;
- benchmark execution;
- permitted training-data or feedback work;
- quality assessment;
- agent/task evaluation;
- red-team or safety testing where authorized;
- comparative model testing;
- contracted AI improvement programs.

**Payment is never assumed.** A provider must explicitly offer compensation, credits, a contract, partner program or other authorized commercial arrangement.

### Free versus paid external AI

Bitey Trainer may use free/open models or free tiers when their licenses and terms permit the intended activity. Paid models may be used when authorized and economically justified.

Trainer must maintain provider metadata such as provider/model, model version, API/contract status, permitted use, evaluation/training permission, cost, rate limits, quality/performance results and commercial opportunity status.

### Privacy and visibility

Bitey Trainer is **underground/internal infrastructure**:

- no public navigation link;
- no BiteFixes footer link;
- no public marketing page;
- no standalone public user destination;
- no Trainer APK.

Only authorized administrators/services may access Trainer operations.

## Notifications for commercial opportunities

When Bitey Trainer identifies a qualified contract, paid AI-training/evaluation opportunity, provider response requiring attention, or important commercial milestone, the system should notify the owner through the configured private channels:

- WhatsApp: **+55 95984377719**
- Email: **ramirezrayler031@gmail.com**

Credentials, API tokens and messaging secrets must never be committed to GitHub. Notification delivery must be implemented server-side using protected secrets and provider-approved APIs.

## Hard architectural boundary

**Bitey Web is the Bitey IA supracerebro.** `bitefixes-backend` is a separate specialized enterprise backend for BiteFixes.com.

Bitey Trainer is subordinate to Bitey IA Web and must not become an independent general AI product or replace Bitey Core.

## Mobile relationship

`bitey-ia-app` is the Android/mobile client of this same Bitey IA product. It should authenticate users and communicate through authorized Bitey IA contracts rather than treating `bitefixes-backend` as its general intelligence layer.

## Enterprise relationship

`bitey-ai` is the authorized enterprise WordPress channel for Bitey IA. It is an integration layer, not a duplicate supracerebro.

## Security principles

- Provider secrets remain server-side.
- External AI usage must be authorized and compliant with provider terms.
- Internal Trainer operations require authentication and authorization.
- User data and commercial opportunity data must be isolated by access policy.
- Browser state is never a security boundary.
- No automated activity may be designed to evade provider controls, quotas, licensing or contracts.

## Ecosystem

| Repository | Product | Objective |
|---|---|---|
| `bitey-web` | **Bitey IA Web** | General Bitey IA web application and Cloudflare supracerebro |
| `bitey-ia-app` | **Bitey IA App** | Android/mobile client for the same Bitey IA product |
| `bitey-ai` | **Bitey IA Enterprise WordPress Plugin** | Authorized WordPress enterprise channel |
| `bitey-trainer` | **Bitey Trainer** | Private internal training/evaluation and commercial-opportunity capability subordinate to Bitey IA |
| `bitefixes-backend` | **BiteFixes Backend** | Specialized BiteFixes enterprise intelligence and API layer |
| `bitefixes-web` | **BiteFixes Web** | BiteFixes.com website/frontend |
| `bitefixes-app` | **BiteFixes App** | BiteFixes mobile customer/business channel |

## Production priorities

1. Keep Bitey Web reliable and AI-first.
2. Complete real user authentication and profile behavior.
3. Ensure conversations and memory remain isolated per user.
4. Align web and Android behavior.
5. Keep Bitey Trainer private and subordinate to Bitey Web.
6. Build a compliant external-AI evaluation and commercial-opportunity layer.
7. Notify the owner of qualified paid opportunities through protected channels.
8. Never expose internal training infrastructure as public navigation.
