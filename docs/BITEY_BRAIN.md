# Bitey Brain — Executive Cognitive Architecture

## Purpose

Bitey Brain is the executive cognitive layer of **Bitey IA Web**, the general/integral AI. It is not another LLM. Its job is to decide how Bitey should perceive, plan, use memory, select tools/models, verify results and act.

```text
Input
 ↓
Perception / Intent / Context
 ↓
BITEY BRAIN
 ├─ goals + constraints
 ├─ task classification
 ├─ decomposition
 ├─ memory priority
 ├─ evidence policy
 ├─ tool selection
 ├─ model selection
 ├─ risk / permissions
 └─ verification plan
 ↓
Memory + Knowledge + Tools + Research
 ↓
Local or verified-free model when useful
 ↓
Evaluation + Contradiction + Confidence
 ↓
Answer / authorized action
 ↓
Learning observation
```

## Independent operation

Bitey must retain a useful deterministic operating core even when every external model is unavailable. This includes routing, validation, calculations, state management, policy checks, tool contracts and memory operations.

AI models are replaceable workers. Bitey can use local/open-weight models and verified free external models, but no single provider is required for the architecture to exist.

## Free profile

The default economic policy is **FREE_ONLY + FAIL_CLOSED**:

- only models/providers verified as free may be selected;
- paid fallback is forbidden;
- local inference is preferred when practical;
- if no free model is available, deterministic capabilities continue or Bitey reports the limitation;
- third-party free quotas are not assumed to be unlimited.

## Tool autonomy

Bitey may design and register new tools from a task requirement, but generated tools must pass a capability contract before execution.

Required fields:

- name and purpose;
- input/output schema;
- permissions;
- cost class;
- side effects;
- timeout and resource limits;
- validation requirements;
- rollback strategy where applicable.

Arbitrary generated code is never trusted merely because an LLM produced it. High-impact tools require explicit authorization and stronger safety gates.

## Memory and knowledge

Supabase/Postgres is the canonical persistent layer for the current architecture. Memory is context, not unquestionable truth. Important claims should retain provenance and confidence where possible.

Neo4j and MongoDB are **not dependencies of Bitey IA Web**.

## Specialized modules

Bitey IA Web can coordinate specialized capabilities through versioned contracts. BiteFixes remains outside the general brain's ownership boundary: BiteFixes owns CRM/SaaS and its Bitey IA Empresarial contextual deployments. SBT remains a separate trading system with its own risk authority.

## Quality target

Do not use an invented IQ score as an engineering metric. Measure task success, evidence grounding, contradiction handling, instruction adherence, tool selection, safety, latency, recovery and learning outcomes.

## Evolution roadmap

1. Deterministic executive loop.
2. Free-model discovery and health-aware fail-closed routing.
3. Supabase-backed cognitive memory and semantic retrieval.
4. Task-decomposition DAG and bounded long-horizon planning.
5. Contradiction detection and confidence calibration.
6. Permissioned Tool Factory.
7. Sandboxed execution for explicitly authorized tools.
8. Capability benchmarks and autonomous recovery tests.
9. Versioned module contracts.
10. Continuous improvement from evaluated outcomes without treating model output as ground truth.

> **Invariant:** Bitey IA Web owns the cognitive loop. Models are tools. Tools are permissioned capabilities. Memory is governed context. Specialized products remain bounded.
