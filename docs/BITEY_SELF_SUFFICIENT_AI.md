# Bitey IA Web — Self-Sufficient AI Architecture

## Objective

Bitey IA Web must be able to function as an AI system in its own right rather than as a wrapper around one external LLM.

External models remain welcome and useful, but they are replaceable workers. The cognitive architecture, memory, planning, evaluation, tools, permissions and recovery logic belong to Bitey.

## Operating model

```text
                    BITEY IA WEB
                         │
                 BITEY BRAIN / CORE
                         │
      ┌──────────────────┼──────────────────┐
      ▼                  ▼                  ▼
   Memory              Tools              Modules
      │                  │                  │
      └──────────────────┼──────────────────┘
                         ▼
                 MODEL FABRIC
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      Local AI       Free Model A   Free Model B
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                 EVALUATION GATE
                         │
                answer / authorized action
```

## Independence levels

### A. No model

Bitey can still validate requests, manage state, calculate, retrieve stored knowledge, select tools and enforce permissions.

### B. Local model

An Ollama/OpenAI-compatible local model provides language and reasoning without an external API quota.

### C. Free model fabric

Bitey discovers and health-checks eligible free providers/models. Selection considers capability, availability, context limits and task fit.

### D. Multiple free models

Complex tasks may be divided among bounded specialist workers. Their outputs are evidence/claims to evaluate, never unquestioned truth.

### E. Tools

Bitey can call authorized deterministic tools and API adapters. Tools may be proposed/created from specifications but must be validated before activation.

## Free profile contract

```text
FREE_ONLY
FAIL_CLOSED
NO_PAID_FALLBACK
```

A free deployment must never silently cross into paid inference. If every external free route is exhausted, Bitey uses local/deterministic capabilities or reports that the capability is unavailable.

This is a **zero-intentional-spend architecture**, not a promise that third-party free quotas are unlimited forever.

## Tool Factory

A tool proposal follows:

```text
Task
 ↓
Capability gap
 ↓
Tool specification
 ↓
Input/output schema
 ↓
Permission + risk + cost policy
 ↓
Implementation
 ↓
Tests / sandbox
 ↓
Registry
 ↓
Authorized execution
 ↓
Evaluation
```

Tools must declare:

- purpose;
- inputs and outputs;
- permissions;
- cost class;
- network access;
- side effects;
- time/resource limits;
- failure behavior;
- rollback strategy when applicable.

No generated tool receives unrestricted system access automatically.

## Self-recovery

When a model fails:

```text
Failure
 ↓
Health / reason classification
 ↓
Retry within bounded policy
 ↓
Try another eligible free/local provider
 ↓
Use deterministic/tool route
 ↓
Reduce task scope if possible
 ↓
Explain limitation
```

When a tool fails, Bitey must not invent the tool result. It should retry only when policy allows, select an alternative capability, or report the limitation.

## Learning without self-corruption

Bitey may learn from evaluated outcomes, but learning is bounded:

- model output is not automatically promoted to truth;
- feedback is stored as an observation;
- high-confidence knowledge requires evidence or repeated validation;
- policy and permission changes require explicit governance;
- tenant/private knowledge remains isolated;
- failed strategies are retained as negative observations where useful.

## Persistence

Supabase/Postgres is the canonical persistence layer. pgvector may provide semantic retrieval inside PostgreSQL.

Neo4j and MongoDB are not part of this architecture.

## Boundaries with the ecosystem

- Bitey IA Web = general/integral AI.
- Bitey IA Empresarial = contextual enterprise implementation owned by BiteFixes.
- BiteFixes CRM/SaaS/agent implementation = owned by BiteFixes.
- `bitey-ai` = WordPress plugin/integration.
- Bitey SBT = separate trading project with its own execution/risk authority.

## Definition of success

Bitey is considered increasingly self-sufficient when it can complete useful tasks with no paid AI API, survive the loss of an individual provider, select and verify tools, retain governed memory, evaluate model outputs, recover from failures and coordinate specialized capabilities without creating competing brains.
