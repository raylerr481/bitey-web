# Bitey IA — Independent Cognitive Core Backend

This backend is the server-side foundation of **Bitey IA**, the central general-purpose cognitive layer of the Bitey ecosystem.

It is intentionally independent from `bitefixes-backend` and from any individual LLM provider.

## Role in the ecosystem

```text
                         BITEY IA
                  INDEPENDENT COGNITIVE CORE
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       JobIA              SBT          BiteFixes
    specialized       specialized      existing
      module             module      contextual IA
```

JobIA and SBT are complementary capabilities. BiteFixes remains its existing contextual enterprise AI. This backend is the central cognitive layer that can provide shared general reasoning/orchestration through explicit contracts without creating unrestricted cross-product data access.

## Cognitive architecture

The backend is model-agnostic. The cognitive layer owns the structure of cognition while external models provide optional inference/language capabilities.

```text
Input
 ↓
Context
 ↓
Intent / Entities / Constraints
 ↓
Evidence & Research
 ↓
Planning / Reasoning
 ↓
Risk & Policy
 ↓
Decision
 ↓
Generation
 ↓
Evaluation / Confidence / Contradiction
 ↓
Memory / Learning observation
```

The codebase includes the cognitive architecture, cognitive model, context engine, cognitive memory, persistent memory, evaluation engine, learning engine, research/deep research, tool orchestration, module registry and provider gateway.

## Provider independence

Bitey uses a provider/model fabric rather than binding cognition to one model.

Supported or planned provider classes include:

- OpenRouter free models with dynamic catalog discovery.
- Local/open-weight models through OpenAI-compatible endpoints.
- Ollama/local inference where configured.
- Other providers only when explicitly authorized by the configured policy.

Default economic policy:

```text
BITEY_COST_MODE=free_only
BITEY_FREE_ONLY_HARD_STOP=true
```

The system must fail closed if a model/provider cannot be verified as allowed under the active policy. There is no silent paid fallback.

Free capacity is not guaranteed to be unlimited. Local inference is the preferred path when quota independence is required and the user's hardware can support it.

## Memory and knowledge

The cognitive core is designed around replaceable storage interfaces.

```text
Working memory       Persistent memory       Knowledge graph
     │                       │                       │
 Redis/edge             Supabase/Postgres         Neo4j
     │                       │                       │
     └───────────────────────┼───────────────────────┘
                             │
                     MongoDB Atlas
                  episodic/document memory
```

Target responsibilities:

- **Supabase/Postgres:** transactional structured data.
- **MongoDB Atlas Free:** episodic/cognitive/document-oriented memory.
- **Neo4j Aura Free:** entities, relationships and knowledge graph traversal.
- **Redis/edge state:** temporary working context and cache.
- **Cloudflare/R2:** edge delivery and object/document storage where required.

These are storage components, not independent intelligence systems. They must remain replaceable and optional.

## Specialized capability contracts

### SBT

SBT consumes Bitey cognition for trading intelligence but remains authoritative for trading-specific execution controls:

```text
Bitey Cognitive Core
        ↓
Trading Intelligence
        ↓
Strategy → Validation → Risk Gate → Permission
        ↓
Demo / Paper → MT5 / Alpaca
```

General AI output cannot bypass the SBT Risk Gate. Live trading remains disabled in the current milestone.

### JobIA

JobIA consumes the same Bitey cognitive core for employment intelligence:

```text
Bitey Cognitive Core
        ↓
Job Intelligence
        ├── CV / profile
        ├── vacancies
        ├── matching
        ├── skills
        ├── interviews
        └── labor-market analysis
```

JobIA is a specialized product, not a second general-purpose brain.

### BiteFixes

BiteFixes is intentionally not migrated into this backend. Its existing contextual enterprise AI remains authoritative for its business/support context, CRM, customers, tickets and authorized company data.

Future integration must use explicit contracts and tenant/authorization boundaries.

## API surface

The backend exposes the Bitey IA contract for web and future clients. Core endpoints include:

- `GET /health`
- `GET /api/v1/capabilities`
- `GET /api/v1/cognitive/status`
- conversation/message APIs

The capabilities/status endpoints expose the current cognitive architecture, memory, learning, provider, module and cost-policy state without requiring a particular model to be the system's identity.

## Module registry

Specialized capabilities are registered rather than embedded into the general brain. A module declares its domain, capabilities and execution boundaries.

For example, SBT is registered as a trading module with an explicit `sbt_risk_gate` execution boundary and live trading disabled.

This keeps the central cognitive layer general while allowing domain systems to remain authoritative for domain-specific actions.

## Security boundaries

- Provider credentials remain server-side secrets.
- No API keys belong in frontend code or documentation.
- LLM/model responses are untrusted until evaluated.
- Private enterprise context is tenant-scoped.
- Cross-module access occurs through explicit contracts.
- Trading permissions are enforced inside SBT, not by conversational prompts.
- Free-only policy is fail-closed.

## Local development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Current phase

The backend has the foundation of the independent cognitive core. The current work is integration and hardening:

1. persistent cognitive memory;
2. MongoDB episodic/document memory where useful;
3. Neo4j knowledge graph integration;
4. provider/model discovery and capability scoring;
5. contradiction/confidence/evidence evaluation;
6. stable versioned contracts for JobIA and SBT;
7. observability and authentication;
8. graceful degradation when a provider or storage service is unavailable.

No Gemini API is required.
