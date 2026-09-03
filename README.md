# Bitey IA Web — Independent Cognitive Core

`bitey-web` is the central web channel and server-side cognitive layer of **Bitey IA**. Bitey IA is the general-purpose intelligence of the ecosystem: it owns the cognitive architecture, orchestration, context, memory, evaluation, learning, capability routing and safety boundaries.

Bitey IA is **not a single-LLM wrapper**. External models are replaceable providers/tools used by the cognitive core.

## Mission

Build an independent, model-agnostic and free-first AI architecture that can continue operating when a particular model, provider or service is unavailable.

The architecture follows:

```text
Perception → Intent → Context → Evidence → Reasoning
        → Planning → Risk/Policy → Decision
        → Generation → Evaluation → Memory/Learning
```

The cognitive architecture is deliberately independent from any individual LLM. Models provide language/inference capabilities when available; Bitey owns the decision structure and orchestration.

## Ecosystem position

```text
                         BITEY IA
                 CENTRAL COGNITIVE CORE
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       JobIA              SBT          BiteFixes
    specialization    specialization   contextual IA
          │                │                │
          ▼                ▼                ▼
     Job Intelligence  Trading Intel.   Enterprise /
     CV / Matching     Market / Risk    Support / CRM
```

**JobIA and Bitey System Bots Trading (SBT) are complementary specialized modules, not independent brains.** BiteFixes is also kept as its existing contextual enterprise AI and is not being replaced by this core.

The central rule is:

> **Bitey IA is the brain. Specialized products are capabilities. Models are tools.**

## Current cognitive core

The backend already contains the foundation for an independent cognitive architecture, including:

- `CognitiveArchitecture` / cognitive frames
- Cognitive Model
- Context Engine
- Cognitive Memory
- Long-term Memory
- Learning Engine
- Evaluation Engine
- Research and Deep Research
- Tool Orchestrator
- Module Registry
- Provider Gateway
- Native/local model support
- Workspace and project context
- Risk and policy boundaries
- Versioned capability discovery

The cognitive frame can represent language, domain, intent, entities, constraints, evidence requirements, confidence, plans and risk flags without depending on an external LLM.

## Provider and model fabric

```text
                 BITEY COGNITIVE CORE
                           │
                  Provider / Model Registry
                           │
                  Capability Matching
                           │
                    Model Selection
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        OpenRouter       Local AI     Other verified
        Free models      / Ollama       providers
              │            │            │
              └────────────┼────────────┘
                           ▼
                    Bitey Evaluation
```

Default policy:

- `FREE_ONLY`
- `FAIL_CLOSED`
- no silent paid fallback
- provider credentials remain server-side
- provider health, capability and availability must be evaluated before use
- local inference is preferred when it provides a practical quota-independent option

### Dynamic free-model discovery

Bitey can discover currently available OpenRouter free models instead of relying exclusively on a permanently hardcoded list. Free status must be verified from the provider catalog/pricing metadata before a model is admitted to the free pool.

The AI Council can compare suitable free providers/models for important tasks, detect contradictions and send the result through Bitey's own evaluation layer. The council is an orchestration mechanism; it does not replace the central cognitive core.

**Free does not mean unlimited.** Bitey guarantees that the configured free-only boundary is not intentionally crossed; it cannot guarantee unlimited external quotas or permanent free availability.

## Local AI

Bitey supports local/open-weight inference through an OpenAI-compatible endpoint when configured. This enables a model provider to run on user-controlled hardware without requiring a hosted AI API.

An optional local Gemma 4 12B provider can participate in the same provider registry as Qwen, DeepSeek, OpenRouter free models and other compatible providers. **No Gemini API is required.**

A local endpoint such as `127.0.0.1` is reachable only by the machine/network where the inference service runs; a public Cloudflare deployment cannot directly access a user's localhost.

## Memory and knowledge fabric

Bitey is being evolved toward a layered memory/knowledge architecture. Storage providers are implementation components, not the brain itself.

```text
                 BITEY COGNITIVE MEMORY
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
   Working           Persistent         Knowledge
   context            memory              graph
       │                 │                 │
     Redis /          Supabase /        Neo4j Aura
     edge state       PostgreSQL
       │                 │
       └──────────┬──────┘
                  ▼
             MongoDB Atlas
        episodic/cognitive data
```

Target responsibilities:

- **Supabase/Postgres:** transactional application state and structured records.
- **MongoDB Atlas Free:** episodic/cognitive/document-oriented memory where appropriate.
- **Neo4j Aura Free:** knowledge graph, entities, relationships and semantic connections.
- **Redis / edge state:** short-lived working context and caching where available.
- **Cloudflare:** web/edge delivery and lightweight state.
- **R2/object storage:** documents and binary objects when required.

These integrations remain replaceable and optional. A temporary failure of one storage layer must not turn that service into a second brain or silently corrupt the cognitive state.

## Neo4j + GraphRAG cognitive support

**Neo4j is not another brain and is not a standalone intelligence layer.** It is one of the internal capabilities that can improve Bitey's cognitive performance by providing structured relationships, connected context, evidence links and graph-based retrieval.

The current implementation adds an optional `Neo4jAdapter` to the Bitey Cognitive Core. It is fail-safe and remains inactive until the Neo4j environment is explicitly configured.

```text
Bitey Cognitive Core
        │
        ▼
   Context Engine
        │
        ├───────────────┐
        ▼               ▼
 Cognitive Memory   Neo4j Graph Context
        │               │
        └───────┬───────┘
                ▼
          Context Fusion
                │
                ▼
            Reasoning
```

The first GraphRAG stage is deliberately **graph-context retrieval**: Bitey can retrieve relevant nodes and their relationships and feed that context into its normal reasoning/evaluation flow. Vector embeddings and Neo4j vector indexes are a later evolution; they are **not claimed as implemented yet**.

Current Neo4j support includes:

- optional connection through server-side environment variables;
- connection health reporting;
- bounded relationship/context retrieval;
- a knowledge status endpoint;
- graph context incorporated into conversational reasoning when available;
- graceful degradation when Neo4j is disabled or unavailable;
- no secrets stored in source code;
- Neo4j remains subordinate to Bitey's central cognitive architecture.

Planned GraphRAG evolution:

```text
Graph Context
     ↓
Embeddings
     ↓
Vector Index
     ↓
Vector Search + Graph Traversal
     ↓
Context Fusion
     ↓
Evidence / Contradiction Evaluation
     ↓
Bitey Reasoning
```

This allows the same knowledge capability to serve general Bitey cognition and specialized domains without creating separate brains.

## Knowledge graph direction

Neo4j can represent relationships such as:

```text
User → Experience → Decision
Decision → Model / Tool / Document
Decision → MarketEvent / Risk
Concept → Concept
```

For SBT this can support relationships between market events, signals, strategies, decisions, risks and evidence. For JobIA it can support skills, roles, vacancies, experiences and career relationships. These are domain capabilities consumed through Bitey contracts.

## Specialized modules

### SBT — Trading Intelligence

Bitey System Bots Trading is a specialized trading module. It does not own the general Bitey brain.

```text
Bitey IA
   ↓
Trading Intelligence
   ↓
Market Intelligence / News / Time Engine
   ↓
Domino State Machine / Contradiction Detection
   ↓
Signal / Strategy
   ↓
Validation
   ↓
Risk Gate
   ↓
Permission
   ↓
Demo / Paper execution
   ↓
MT5 / Alpaca integrations
```

The SBT backend remains authoritative for trading permissions and risk controls. **Live trading remains disabled in the current milestone.** News or model output must never bypass the SBT Risk Gate.

### JobIA — Employment Intelligence

JobIA is a specialized employment/career capability using Bitey IA as its central cognitive layer.

```text
Bitey IA
   ↓
Job Intelligence
   ├── CV / profile analysis
   ├── Vacancy analysis
   ├── Skills and competency mapping
   ├── Candidate ↔ vacancy matching
   ├── Interview preparation
   └── Labor-market intelligence
```

JobIA may evolve its own product UX and domain services, but it does not create a competing general-purpose brain.

### BiteFixes — existing contextual AI

BiteFixes remains an existing contextual enterprise AI with its own business/support context, CRM, customers, tickets, services and authorized company data.

**BiteFixes is not being replaced or refactored as part of this cognitive-core evolution.** Integration with Bitey IA should occur through explicit contracts and authorized context boundaries.

## Contract-based interconnection

```text
Web / Android / API channel
            │
            ▼
       Bitey IA API
            │
            ▼
  Independent Cognitive Core
            │
      ┌─────┼─────┐
      ▼     ▼     ▼
    JobIA   SBT  BiteFixes
      │     │      │
      └─────┼──────┘
            ▼
   Authorized domain result
```

A specialized module can request Bitey cognition, context processing or reasoning through an explicit contract. It cannot arbitrarily access another module's private data.

## Safety and authority boundaries

- Bitey owns general cognitive orchestration.
- Specialized products own their domain-specific operations.
- SBT Risk Engine/Risk Gate is authoritative for trading execution safety.
- Enterprise/private BiteFixes context stays within authorized tenant boundaries.
- Provider secrets remain server-side.
- LLM output is untrusted until evaluated against the relevant policy/contract.
- Evidence is preferred for high-impact decisions.
- Memory is context, not unquestionable truth.
- No provider can silently cross the configured billing boundary.

## Runtime flow

```text
Input
  ↓
Context Engine
  ↓
Cognitive Memory + Graph Context
  ↓
Tools / Research / Deep Research
  ↓
Cognitive Architecture
  ↓
Module Routing
  ↓
Provider / Model Selection
  ↓
Generation / Reasoning
  ↓
Evaluation / Contradiction / Confidence
  ↓
Policy & Safety
  ↓
Response or authorized module action
  ↓
Memory + Learning observation
```

This architecture allows Bitey to degrade gracefully: deterministic tools, stored knowledge, local models or another verified free provider can continue to provide useful capabilities when one model is unavailable.

## Security and data boundaries

- No credentials or API keys in frontend code or README files.
- Provider credentials are server-side secrets.
- Private enterprise data is tenant-scoped.
- Specialized modules expose only authorized capabilities.
- Cross-module communication uses explicit contracts.
- Trading execution remains isolated from general conversational reasoning.
- External model responses are treated as untrusted input to the evaluation/policy layer.

## Runtime configuration for Neo4j

The code expects Neo4j credentials only as server-side environment variables:

```text
NEO4J_ENABLED=true
NEO4J_URI=<Aura connection URI>
NEO4J_USERNAME=<database user>
NEO4J_PASSWORD=<database password>
NEO4J_DATABASE=neo4j
NEO4J_MAX_RESULTS=8
```

Do not commit these values to GitHub. The application remains functional with `NEO4J_ENABLED=false` until an Aura instance is created and connected.

## Current infrastructure direction

```text
Cloudflare
   │
   ├── Bitey IA Web
   └── specialized web channels
            │
            ▼
     Bitey Cognitive API
            │
     ┌──────┼────────┐
     ▼      ▼        ▼
 Supabase MongoDB  Neo4j
     │      │        │
     └──────┼────────┘
            ▼
      Provider Fabric
            │
   ┌────────┼─────────┐
   ▼        ▼         ▼
OpenRouter Local AI  Future
 Free      /Ollama   providers
```

The objective is **interchangeable infrastructure**: Bitey should not become dependent on one database, one graph service, one hosting provider or one AI model.

## Development priorities

1. Keep Bitey IA Web stable as the central AI channel.
2. Complete persistent cognitive memory and knowledge integrations.
3. Connect the Neo4j Aura instance and validate graph context retrieval.
4. Add embeddings/vector indexes and full GraphRAG retrieval after the graph-context stage is validated.
5. Formalize provider/model capability scoring and health-aware fallback.
6. Strengthen confidence, contradiction and evidence evaluation.
7. Define stable versioned contracts for JobIA and SBT.
8. Connect SBT intelligence to the central cognitive core without weakening its Risk Gate.
9. Connect JobIA capabilities to the same central cognitive core.
10. Preserve BiteFixes as the already-working contextual enterprise AI.
11. Keep web and future Android channels aligned to the same Bitey IA identity and contracts.
12. Maintain `FREE_ONLY + FAIL_CLOSED` and never silently introduce paid inference.
13. Keep local open-weight inference as a viable quota-independent option.
14. Add observability, authentication, tenant isolation and recovery mechanisms as the ecosystem grows.

## Project status

Bitey IA Web already contains the foundation of the independent cognitive core. The current phase is **integration and evolution**, not replacement: connect memory, knowledge graph, provider discovery, specialized capabilities and evaluation into a coherent Bitey architecture while preserving existing working systems.

Neo4j integration is now present in the backend as an optional cognitive-support component. The remaining infrastructure step is to connect a running Neo4j Aura instance and then evolve from graph-context retrieval to full vector + graph GraphRAG.

No Gemini API is required by this architecture.
