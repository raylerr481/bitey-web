# Bitey IA — Supabase-First Cognitive Architecture

## Non-negotiable boundary

BiteFixes is an external specialized system whose existing structure is immutable.
Bitey IA may integrate with BiteFixes only through explicit API/contract adapters.
Bitey IA must never migrate, refactor, rename, copy, or directly couple to BiteFixes operational tables.

## Canonical cognitive persistence

The canonical persistence layer for Bitey IA is Supabase/PostgreSQL in the dedicated Bitey IA project.

Use the `bitey` schema for cognitive state:

- `cognitive_sessions`
- `memories`
- `knowledge_nodes`
- `knowledge_edges`
- `evidence`
- `evaluations`
- `capabilities`
- `providers`
- `learning_events`
- `module_contracts`

`memories.embedding` is the semantic retrieval field and uses pgvector.

## Removed optional organs

MongoDB, Neo4j and hosted Qdrant are not required by the current architecture.
Their adapters may remain temporarily for backward compatibility, but they must be disabled by default and must not be required for startup or cognition.

## Cognitive flow

```text
Perception
  -> Intent
  -> Context
  -> Memory (Supabase + pgvector)
  -> Evidence / Research
  -> Reasoning
  -> Planning
  -> Risk / Policy
  -> Decision
  -> Generation
  -> Evaluation
  -> Memory / Learning
```

## Module boundary

```text
                         Bitey IA
                    Cognitive Core
                          |
             +------------+------------+
             |            |            |
           JobIA          SBT       BiteFixes
             |            |            |
        adapter/API   adapter/API   existing API
```

JobIA and SBT may evolve to consume Bitey cognitive capabilities. BiteFixes remains independently owned and operationally intact.

## Security model

- Browser/mobile clients never receive the Supabase service-role key.
- Cognitive writes happen server-side through the Bitey API.
- RLS must be enabled before exposing any `bitey` table to anon/authenticated clients.
- No policy should grant public access to cognitive memory by default.
- Provider credentials are never stored in memories or knowledge records.
- Module adapters receive only the minimum context required by their contract.
- LLM output remains untrusted until evaluation and policy checks complete.

## Free-first policy

Bitey remains functional if an optional model/provider/vector service disappears.
Supabase/PostgreSQL + pgvector is the default durable cognitive store; local inference and verified free providers remain replaceable execution tools.
