# Bitey Brain — Executive Cognitive Architecture v1

## Purpose

Bitey Brain is the executive cognitive layer of Bitey IA. It is **not another LLM** and does not compete with the provider/model layer. Its job is to decide how Bitey should think before a model generates an answer.

```text
User input
   ↓
Perception / Context
   ↓
BITEY BRAIN
   ├─ task classification
   ├─ complexity estimation
   ├─ ambiguity detection
   ├─ evidence policy
   ├─ memory priority
   ├─ tool priority
   ├─ reasoning mode
   ├─ risk policy
   └─ verification policy
   ↓
Tools / Research / Memory / Knowledge
   ↓
Provider / Local Model
   ↓
Evaluation + Contradiction checks
   ↓
Response / authorized capability
   ↓
Learning observation
```

## Why this matters

A strong conversational model alone does not define a complete cognitive system. Bitey therefore owns the executive loop while models remain replaceable inference engines.

The brain uses lightweight deterministic signals to choose between direct response, structured reasoning, evidence-first research, decomposition/verification, and guarded decision modes. This improves consistency without requiring MongoDB, Neo4j, or a particular AI provider to be online.

## Cognitive contract

Every message receives a `BrainState` containing:

- task class/domain;
- complexity and ambiguity;
- evidence requirement;
- risk level;
- reasoning mode;
- memory priority;
- preferred tools;
- verification requirement;
- execution policy;
- goals and constraints.

The contract is placed into runtime context and a compact executive directive is supplied to the selected model.

## Degraded operation

MongoDB and Neo4j are optional supporting memory/knowledge systems. Their temporary absence does not disable the Brain. Bitey can continue with the context engine, Supabase-backed state where configured, local computation, tools, research and available models.

When Neo4j returns later, graph context can be reintroduced without changing the executive architecture. MongoDB can likewise be restored as an episodic/document memory provider without becoming a second brain.

## Quality target

The project should aim for **high reasoning quality comparable in behavior to strong frontier assistants**, but should not claim a literal IQ score. IQ is not a valid engineering metric for a software architecture. Bitey's measurable targets are instead task accuracy, evidence grounding, contradiction handling, instruction adherence, tool selection, safety, latency, recovery and learning from feedback.

## Next evolution

1. Add explicit contradiction detection between evidence, memory and model claims.
2. Add task decomposition with dependency graphs for complex requests.
3. Add confidence calibration using evaluation outcomes.
4. Add salience-weighted memory retrieval.
5. Add provider/model capability scoring and adaptive routing.
6. Add vector retrieval when the storage layer is available.
7. Add graph + vector fusion when Neo4j is available.
8. Connect JobIA and SBT through stable capability contracts.
9. Keep BiteFixes isolated behind authorized contracts.

The invariant remains:

> **Bitey IA is the brain. Models are tools. Databases and graphs are memory/knowledge organs. Specialized products are capabilities.**
