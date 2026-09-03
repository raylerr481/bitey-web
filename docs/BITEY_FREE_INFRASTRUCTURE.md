# Bitey IA — Free-First Cognitive Infrastructure

## Principle

Bitey Brain owns cognition. Infrastructure supplies persistence, retrieval, research, model execution and tools. No external service becomes the brain.

The architecture is **free-first and fail-closed**: the free profile never silently invokes paid inference.

## Current architecture

| Organ | Technology | Role |
|---|---|---|
| Executive cognition | Bitey Brain | planning, routing, risk, verification | 
| Persistent state | Supabase/Postgres | canonical structured state and memory |
| Semantic memory | PostgreSQL/pgvector when enabled | embeddings and semantic retrieval |
| Local inference | Ollama-compatible endpoint | quota-independent local AI |
| External inference | verified free OpenAI-compatible providers | model diversity/failover |
| Research | Web/deep-research layer | current evidence |
| Evaluation | Bitey evaluator | quality/contradiction gate |
| Learning | Bitey learning engine | bounded learning observations |
| Tools | Bitey Tool Registry | deterministic/API capabilities |

**Neo4j and MongoDB are excluded.** Qdrant is not required for the canonical architecture; pgvector in Supabase is the preferred semantic-memory direction.

## Free execution strategy

1. Deterministic Bitey tools first when an LLM is unnecessary.
2. Local/open-weight inference when available.
3. Verified free external models/providers.
4. Bounded multi-model cooperation for complex tasks when every selected model is free.
5. Web research only when freshness/evidence is needed.
6. If no free route exists, fail closed rather than spend money.

## Self-sufficiency layers

```text
Layer 0  Deterministic cognition
Layer 1  Local AI
Layer 2  Verified free model fabric
Layer 3  Tool execution
Layer 4  Research / external evidence
Layer 5  Specialized modules
Layer 6  Evaluation + learning
```

The layers are additive. Loss of an upper layer must not destroy the lower layers.

## Tool Factory

Bitey is designed to create new tools from requirements, but the creation process is governed:

```text
Task requirement
   ↓
Tool specification
   ↓
Schema + permission + cost + risk validation
   ↓
Implementation/adapter
   ↓
Tests / sandbox
   ↓
Registry
   ↓
Authorized execution
   ↓
Evaluation
```

Tools should prefer deterministic code or narrowly scoped API adapters. Arbitrary model-generated shell/code execution is disabled by default.

## Memory design

Use Supabase/Postgres for:

- conversation and working-state persistence;
- episodic summaries;
- semantic/knowledge records;
- user/project context;
- tool observations;
- learning observations;
- provenance and confidence metadata.

Use PostgreSQL row-level security and tenant scoping wherever enterprise context is stored.

## Recommended open/free components

- Ollama for local open-weight model serving.
- PostgreSQL/pgvector through Supabase for semantic retrieval.
- OpenTelemetry for vendor-neutral telemetry.
- Lightweight OpenAI-compatible adapters instead of locking Bitey to one provider.
- Sandboxed runtimes for explicitly authorized tool execution.

Hosted free tiers must be treated as replaceable because quotas and policies can change.

## Priority roadmap

### High
- Harden free provider discovery and health scoring.
- Complete Supabase cognitive memory.
- Add task-decomposition DAGs.
- Add contradiction and confidence engines.
- Implement permissioned Tool Factory.
- Add provenance ledger.

### Medium
- Local embeddings and pgvector retrieval.
- Tool sandbox and resource limits.
- Observability and recovery tests.
- Capability benchmark suite.
- Scheduled memory consolidation.

### Advanced
- Long-horizon planning.
- Specialist workers controlled by one Bitey Brain.
- Self-evaluation loops with bounded budgets.
- Autonomous recovery from provider/tool failures.
- Continuous capability discovery without automatic permission escalation.

**Invariant:** Bitey IA Web must be useful with zero paid AI spend. External free models improve capability; they do not define or own Bitey's cognition.
