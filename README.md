# Bitey IA Web

`bitey-web` is **Bitey IA Web**, the web channel and Cloudflare-hosted intelligence layer of Bitey IA.

## Product role

Bitey IA is the general intelligence layer of the ecosystem. Bitey IA Web is one channel to that intelligence. `bitey-ia-app` is another channel to the same Bitey IA, not a separate brain.

## AI provider and model policy

Bitey IA operates with a **FREE_ONLY + FAIL_CLOSED** policy by default.

The important distinction is:

- AI models such as Gemma, Qwen, DeepSeek, Groq-hosted models and other providers are **tools consulted by Bitey**.
- Bitey owns the orchestration, memory, context, evaluation, feedback, routing knowledge and learning loop.
- Models do not become Bitey and do not own Bitey's learning system.
- There is **no silent paid fallback**.
- If a provider cannot be verified as free, Bitey does not use it while `BITEY_COST_MODE=free_only` is active.
- If no verified free provider is available, Bitey stops with a billing-risk message instead of spending money.

### Dynamic OpenRouter Free Model Registry

Bitey should not require a hardcoded list of every free model on OpenRouter. When OpenRouter is enabled, Bitey can query the OpenRouter model catalog and discover models whose model ID is a free variant and whose prompt/completion pricing is zero.

The discovered models are registered in the same provider/model pool used by the AI Council. This means a newly published free model can become available to Bitey without a code change, subject to the catalog and policy checks.

OpenRouter currently provides a dedicated `openrouter/free` router that selects among currently available free models and filters for request capabilities. OpenRouter also publishes a changing catalog of zero-priced free variants. citeturn0search0turn0search2

Bitey nevertheless keeps model-specific free variants as the preferred deterministic path: this lets Bitey evaluate capabilities and select the best model for a task instead of blindly relying on a random free-model route.

### Free does not mean unlimited

Bitey can guarantee **no intentional billing while FREE_ONLY is enforced**. It cannot guarantee that an external provider will offer unlimited requests, unlimited tokens, permanent availability, or permanent free pricing.

For example, OpenRouter's current Free plan documents a request limit, and its free catalog changes over time. Some models can leave the free tier. citeturn0search9turn0search16

Therefore Bitey's promise is stronger and more precise:

> **Bitey never crosses the configured billing boundary. If free capacity is exhausted or disappears, Bitey waits/stops instead of charging.**

For genuinely quota-independent inference, local open-weight models are the preferred option because the inference cost is controlled by the user's own hardware rather than a hosted provider quota.

### AI Council selection

The registry feeds the Bitey AI Council. For each task, Bitey can evaluate the available free models by capability and choose the most appropriate one. For important tasks it can consult multiple free models, compare answers, detect contradictions and let Bitey evaluate the result.

Conceptually:

```text
OpenRouter catalog / local providers / other verified free providers
                              │
                              ▼
                    Bitey Model Discovery
                              │
                              ▼
                    AI Provider/Model Registry
                              │
                              ▼
                     Capability evaluation
                              │
                              ▼
                         AI Council
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
          best free model          multi-model review
                 │                         │
                 └────────────┬────────────┘
                              ▼
                   Bitey evaluation layer
                              │
                              ▼
                  memory / feedback / learning
```

## Gemma 4 12B

Bitey IA Web supports **Google Gemma 4 12B** as an optional local provider named `gemma-4-12b-local`.

- Model: `google/gemma-4-12B-it`
- License: Apache 2.0
- Local endpoint: OpenAI-compatible `/v1/chat/completions`
- Default endpoint: `http://127.0.0.1:50305/v1`
- No Gemini API is required for this local integration.
- Recommended runtimes include llama.cpp, LM Studio and LiteRT-LM-compatible OpenAI endpoints.
- Gemma participates in the **same Bitey provider registry and AI Council** as other providers; it is not a separate intelligence subsystem.

Enable it in the Bitey IA backend with:

```text
BITEY_COST_MODE=free_only
BITEY_FREE_ONLY_HARD_STOP=true
GEMMA_4_12B_ENABLED=true
GEMMA_4_12B_ENDPOINT=http://127.0.0.1:50305/v1
GEMMA_4_12B_MODEL=google/gemma-4-12B-it
GEMMA_4_12B_PRIORITY=3
```

The endpoint must be reachable from the backend process. A deployed Cloudflare backend cannot directly reach `127.0.0.1` on a user's PC; for production hosting, use an explicitly authorized reachable inference endpoint or keep Gemma local.

## OpenRouter configuration

```text
BITEY_COST_MODE=free_only
BITEY_FREE_ONLY_HARD_STOP=true
OPENROUTER_ENABLED=true
OPENROUTER_API_KEY=<server-side-secret>
```

Optional deterministic entries can still be configured:

```text
OPENROUTER_QWEN_MODEL=qwen/qwen3-4b:free
OPENROUTER_DEEPSEEK_MODEL=deepseek/deepseek-chat-v3-0324:free
```

Bitey validates the free-variant ID and zero pricing before dynamically registering additional OpenRouter models. API credentials remain server-side and are never placed in frontend code.

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
- Free-only enforcement is fail-closed: billing risk is never resolved by silently selecting a paid model.

## Product development principle

The ecosystem should reuse proven engineering knowledge without copying protected expression from competitors. Every new product feature should have an independent Bitey information architecture, implementation and visual treatment.

## Production priorities

1. Keep Bitey IA Web reliable and AI-first.
2. Keep web and Android channels aligned to the same Bitey IA identity/contracts.
3. Maintain the dynamic free-model registry and hard no-billing boundary.
4. Integrate JobIA with validated Bitey Trainer capabilities.
5. Integrate Bitey SBT through safe, versioned trading APIs.
6. Build the SBT web frontend as an independent product, not as an extension of `bitey-web`.
7. Preserve Bitey IA Empresarial as the contextual enterprise layer for BiteFixes.
8. Maintain authentication, privacy, tenant isolation and observability.
9. Keep local Gemma 4 12B available as a zero-hosting-cost inference option.
