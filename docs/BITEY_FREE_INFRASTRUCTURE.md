# Bitey IA — Free-First Cognitive Infrastructure

## Principle

Bitey Brain owns cognition. Infrastructure services provide memory, knowledge, retrieval, observability and model execution. No external service is allowed to become the brain.

## Current/ready organs

| Organ | Technology | Role | Optional |
|---|---|---|---|
| Executive cognition | Bitey Brain | planning/routing/risk/verification | No |
| Relational state | Supabase/Postgres | durable structured state | Yes |
| Episodic memory | MongoDB | conversations/experiences/documents | Yes |
| Knowledge graph | Neo4j | entities/relations/causal links | Yes |
| Semantic memory | Qdrant | vector retrieval | Yes |
| Local inference | Ollama-compatible endpoint | private/local model execution | Yes |
| External inference | OpenAI-compatible providers | model diversity/failover | Yes |
| Research | Web/deep research layer | current evidence | Yes |
| Evaluation | Bitey evaluator | quality gate | No |
| Learning | Bitey learning engine | bounded learning observations | No |

## MongoDB design

Use MongoDB for episodic memory rather than facts that require relational integrity. Suggested collections:

- `cognitive_episodes`
- `conversation_summaries`
- `user_preferences`
- `tool_observations`
- `learning_experiences`

Never store provider secrets or raw credentials in cognitive memory.

## Neo4j design

Use graph nodes for stable entities and relationships:

- `Person`, `Organization`, `Project`, `Concept`, `Capability`, `Event`, `Document`, `Tool`, `Model`, `Decision`, `Risk`.

Useful relationships:

- `KNOWS`
- `DEPENDS_ON`
- `PART_OF`
- `SUPPORTS`
- `CONTRADICTS`
- `DERIVED_FROM`
- `USED_BY`
- `CAUSED_BY`
- `RELEVANT_TO`

The graph should capture relationships and provenance, not duplicate the entire chat history.

## Vector memory design

Qdrant is prepared as the semantic retrieval organ. A point should contain an embedding plus payload such as:

`memory_id`, `tenant_id`, `domain`, `source`, `conversation_id`, `importance`, `confidence`, `created_at`, `expires_at`, `text_hash`.

Use hybrid retrieval where possible: lexical filters + vector similarity + reranking. Qdrant supports payload filtering and hybrid retrieval patterns. See official documentation for current deployment options.

## Free-first execution strategy

1. Local model via Ollama when the user's computer is available.
2. Confirmed free provider endpoints when configured.
3. Provider failover rather than blind multi-model consensus.
4. Local tools for calculations and deterministic work.
5. Web research only when freshness/evidence is required.
6. Optional cloud services only behind explicit configuration and the existing cost gate.

## Recommended future components

### High priority
- Qdrant semantic memory + local embeddings.
- Contradiction engine.
- Task decomposition DAG.
- Confidence calibration.
- Model capability registry.
- Prompt/context budget manager.
- Provenance ledger for important claims.
- Benchmark suite for Bitey Intelligence Score.

### Medium priority
- OpenTelemetry traces and metrics.
- Langfuse-compatible evaluation/observability.
- Ollama local inference adapter.
- MCP capability registry and permission scopes.
- Reranker service.
- Document ingestion/chunking pipeline.
- Scheduled memory consolidation.

### Advanced
- GraphRAG fusion: vector retrieval → Neo4j expansion → reranking → Brain verification.
- Causal hypothesis graph.
- Long-horizon planning and task DAG execution.
- Self-critique/evaluator loops with bounded budgets.
- Personalization profiles separated from general knowledge.
- Multi-agent specialist workers controlled by one Bitey Brain.

## Free/open-source candidates to evaluate

- Ollama for local model serving; its API is OpenAI-compatible.
- Qdrant for vector/semantic retrieval, including local/embedded options.
- LiteLLM for a unified OpenAI-compatible gateway and provider routing when its deployment fits the project.
- OpenTelemetry for vendor-neutral telemetry.
- PostgreSQL/pgvector where keeping vector data in Supabase is simpler than adding Qdrant.

Always verify current free-tier limits before depending on a hosted service. The architecture must remain functional when any optional provider disappears.
