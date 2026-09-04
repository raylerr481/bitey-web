# Bitey IA Web — General Integral AI

`bitey-web` is **Bitey IA Web**, the general/integral Bitey IA architecture. It is the general-purpose intelligence of the ecosystem, conceptually comparable to a general assistant such as ChatGPT.

It is not the BiteFixes CRM, not BiteFixes SaaS and not the WordPress plugin. Those remain separate product boundaries.

## Mission

Build an AI that can operate as independently as possible from any single external model: it must have its own cognitive architecture, memory, planning, evaluation, tool orchestration and capability routing, while using external or local AI models when they improve language/inference quality.

The target is **free-first by design**:

- free external models only when the free profile is selected;
- no silent paid fallback;
- local/open-weight models as the quota-independent path;
- deterministic tools for work that does not require an LLM;
- graceful degradation when a provider disappears;
- Supabase as the canonical persistent data/knowledge layer.

Free services can have quotas or change their policies, so the architecture guarantees **no intentional paid inference**, not unlimited third-party usage.

## Cognitive architecture

```text
INPUT
  ↓
Perception / Intent / Context
  ↓
BITEY BRAIN
  ├── goals + constraints
  ├── task decomposition
  ├── memory selection
  ├── evidence policy
  ├── tool selection
  ├── model selection
  ├── risk / permission policy
  └── verification plan
  ↓
Memory + Knowledge + Tools + Research
  ↓
Free/local/external model when useful
  ↓
Evaluation + contradiction + confidence
  ↓
Answer / authorized action
  ↓
Learning observation + memory consolidation
```

**Bitey owns the cognitive loop. Models are replaceable inference tools.**

## Skywork-style workspace layer

Bitey IA now adds a **Skywork-style workspace experience** without copying Skywork's implementation or changing Bitey's core principle. The workspace is an orchestration surface over the existing cognitive engine.

It exposes capability contracts for Chat, web/deep research, documents, presentations, spreadsheets, code, files, projects and bounded agent/task orchestration.

```text
Workspace UI
     ↓
Bitey Workspace API
     ↓
Bitey Cognitive Core / Brain
     ↓
Tools + Research + Memory + Model workers
     ↓
Evaluation / policy
     ↓
Artifact or authorized result
```

This is intentionally **not** a second brain. Bitey remains the decision-maker.

## Self-sufficient operation

Bitey IA Web must not stop functioning simply because one model or provider is unavailable.

### Level 0 — deterministic core

Can perform routing, validation, calculations, state transitions, policy checks, memory operations and other deterministic tasks without an LLM.

### Level 1 — local AI

When available, a local/open-weight model through an OpenAI-compatible endpoint provides private, quota-independent inference.

### Level 2 — verified free providers

Bitey can dynamically discover and select currently free-compatible providers/models. Free status must be verified before admission to the free pool.

### Level 3 — model cooperation

For complex tasks Bitey can use multiple eligible free models sequentially or as bounded specialist workers. They are workers, not separate brains. Bitey's evaluator remains authoritative.

### Level 4 — tool execution

Bitey can select authorized tools to obtain evidence or perform deterministic work. Tools are capability contracts with explicit permissions, inputs, outputs and safety limits.

## Tool creation architecture

Bitey is designed to **create and register new tools**, but not by blindly executing arbitrary generated code.

```text
Need detected → Specification → Validation → Implementation → Tests → Registry → Authorized execution → Evaluation
```

## Model independence

The configured free profile is a hard economic boundary: if no eligible free model is available, Bitey does not silently spend money. It can fall back to deterministic tools, local inference or explain that the requested capability is temporarily unavailable.

No Gemini API is required.

## Memory and knowledge

**Supabase/Postgres is the canonical persistent layer.** Memory is organized conceptually as working context, episodic experience, semantic knowledge, user/project context and learned observations.

No Neo4j or MongoDB dependency is part of the current architecture.

## Modules

- JobIA — employment intelligence.
- Bitey SBT — trading intelligence, kept operationally isolated and subject to its own risk gate.
- Other future modules through explicit capability contracts.

### BiteFixes boundary

BiteFixes is separate and owns its CRM, SaaS and AI-agent implementation. **Bitey IA Empresarial** is the contextual enterprise implementation used by BiteFixes. Bitey IA Web may provide general intelligence capabilities through contracts, but it does not absorb BiteFixes CRM/SaaS.

## WordPress boundary

`bitey-ai` is the **Bitey IA WordPress plugin**. It provides the Web widget/globe and integration transport. It is not the general Bitey IA Web brain.

## Security and autonomy rules

- Models are untrusted inputs to the evaluator.
- Tools are permissioned capabilities, not unrestricted shell access.
- External actions require explicit capability authorization.
- Secrets remain server-side.
- Tenant/private enterprise context is isolated.
- High-impact actions require stronger policy gates.
- Free-only mode fails closed.
- No provider can silently change the billing mode.

## Current infrastructure

```text
                BITEY IA WEB
                     │
       ┌─────────────┼──────────────────┐
       ▼             ▼                  ▼
   Cognitive       Tool              Workspace
     Core        Registry              Hub
       │             │                  │
       └─────────────┼──────────────────┘
                     ▼
             Supabase / pgvector
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Local AI      Free model     Research/Web
   / Ollama       providers       tools
```

## Roadmap

1. Complete the deterministic executive loop.
2. Harden free-model discovery, health and fail-closed routing.
3. Complete Supabase-backed cognitive memory and semantic retrieval.
4. Add task-decomposition DAGs and bounded long-horizon planning.
5. Connect Workspace tasks directly to the bounded cognitive runtime.
6. Add contradiction detection and confidence calibration.
7. Expand permissioned artifact generation for documents, slides and spreadsheets.
8. Add sandboxed code execution only where explicitly authorized.
9. Add self-tests, capability benchmarks and recovery tests.
10. Connect specialized modules through versioned contracts.
11. Keep BiteFixes CRM/SaaS and Bitey IA Empresarial outside the general brain's ownership boundary.

**Core invariant:** Bitey IA Web is the general/integral AI. It can use other AIs, tools and modules, but it does not depend on one of them to exist, and the free profile never silently becomes paid.
