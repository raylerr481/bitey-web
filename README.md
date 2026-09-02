# Bitey IA Web

`bitey-web` is **Bitey IA Web**, the web channel and Cloudflare-hosted intelligence layer of Bitey IA.

## Product role

Bitey IA is the general intelligence layer of the ecosystem. Bitey IA Web is one channel to that intelligence. `bitey-ia-app` is another channel to the same Bitey IA, not a separate brain.

## AI provider policy

Bitey IA uses a **free-first provider gateway**. Providers are selected explicitly by configuration; there is no silent switch to a paid provider.

### Gemma 4 12B

Bitey IA Web supports **Google Gemma 4 12B** as an optional local provider named `gemma-4-12b-local`.

- Model: `google/gemma-4-12B-it`
- License: Apache 2.0
- Local endpoint: OpenAI-compatible `/v1/chat/completions`
- Default endpoint: `http://127.0.0.1:50305/v1`
- No Gemini API is required for this local integration.
- Recommended runtimes include llama.cpp, LM Studio and LiteRT-LM-compatible OpenAI endpoints.

Enable it in the Bitey IA backend with:

```text
BITEY_COST_MODE=free_only
GEMMA_4_12B_ENABLED=true
GEMMA_4_12B_ENDPOINT=http://127.0.0.1:50305/v1
GEMMA_4_12B_MODEL=google/gemma-4-12B-it
GEMMA_4_12B_PRIORITY=3
```

The endpoint must be reachable from the backend process. A deployed Cloudflare backend cannot directly reach `127.0.0.1` on a user's PC; for production hosting, use an explicitly authorized reachable inference endpoint or keep Gemma local.

Google documents Gemma 4 12B as a model designed for local laptop inference and approximately 16 GB of VRAM/unified memory. The model is also available as open weights through the Gemma ecosystem.

## Ecosystem architecture

```text
                         BITEY IA
                    GENERAL INTELLIGENCE
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       JobIA           Bitey SBT        BiteFixes
          │                │                │
   Bitey Trainer      SBT Web/App     Enterprise IA
      (motor)          (specialized)   (contextual)
```

All products are interconnected through explicit APIs/contracts, while their frontends, user experiences, operational data and product identities remain independent.

## Bitey System Bots Trading

`bitey-system-bots-trading` is the specialized trading intelligence and platform backend. `bitey-system-bots-trading-app` is its mobile channel. A separate SBT web frontend is planned for independent Cloudflare deployment.

Bitey SBT is an **original Bitey product**. It can implement broad, non-exclusive market capabilities such as research, strategy construction, simulation, comparison, validation, publishing and monitoring, but its UX, terminology, architecture, scoring, orchestration, copy and visual identity must be designed independently.

Bitey SBT must not become a visual, textual or code clone of TradingKit or any other competitor. Competitor products may be studied only as market references; implementation decisions must be derived from Bitey's own product requirements.

## BiteFixes / Bitey IA Empresarial

BiteFixes is an enterprise product with its own Web and App channels. **Bitey IA Empresarial** operates with BiteFixes business context: CRM, customers, tickets, services, knowledge, workflows and authorized company data.

Private BiteFixes data remains inside authorized enterprise boundaries and must not be exposed to unrelated products.

## JobIA and Bitey Trainer

JobIA is a separate product in development. `bitey-trainer` is its internal intelligence/training engine, not a mobile application.

## WordPress integration

`bitey-ai` is the configurable Bitey IA Enterprise WordPress integration/channel layer. It is not the general intelligence layer and not a duplicate backend.

## Interconnection rule

```text
Independent frontend
       │
       ▼
Specialized backend
       │
       ├── authorized platform data
       └── explicit Bitey IA contract
                    │
                    ▼
                BITEY IA
```

Interconnection does not mean shared unrestricted memory. Sensitive/private information stays within its authorized product and tenant boundary.

## Data and security

- User and company data remain isolated by authorization and tenant boundaries.
- Provider credentials remain server-side.
- Specialized products communicate with Bitey IA through explicit contracts.
- Bitey IA remains the general intelligence layer.
- Specialized products remain authoritative for their own domain operations.
- BiteFixes private operational context remains restricted to authorized enterprise flows.
- SBT trading controls remain authoritative inside the SBT backend/Risk Engine.

## Product development principle

The ecosystem should reuse proven engineering knowledge without copying protected expression from competitors. Every new product feature should have an independent Bitey information architecture, implementation and visual treatment.

## Production priorities

1. Keep Bitey IA Web reliable and AI-first.
2. Keep web and Android channels aligned to the same Bitey IA identity/contracts.
3. Integrate JobIA with validated Bitey Trainer capabilities.
4. Integrate Bitey SBT through safe, versioned trading APIs.
5. Build the SBT web frontend as an independent product, not as an extension of `bitey-web`.
6. Preserve Bitey IA Empresarial as the contextual enterprise layer for BiteFixes.
7. Maintain authentication, privacy, tenant isolation and observability.
8. Maintain a free-first AI provider path, including optional local Gemma 4 12B inference.
