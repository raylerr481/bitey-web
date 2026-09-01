# Bitey IA Web

`bitey-web` is **Bitey IA Web**, the web channel and Cloudflare-hosted **Supracerebro of Bitey IA**.

## Product role

Bitey IA is the general intelligence layer of the ecosystem. Bitey IA Web is one channel to that intelligence. `bitey-ia-app` is another channel to the same Bitey IA, not a separate brain.

```text
                         BITEY IA
                    SUPRACEREBRO / IA
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

`bitey-ai` is the configurable Bitey IA Enterprise WordPress integration/channel layer. It is not the general Supracerebro and not a duplicate backend.

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
