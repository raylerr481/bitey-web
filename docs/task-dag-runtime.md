# Bitey IA bounded Task DAG

Bitey may decompose complex workspace requests into a dependency graph, but the graph is bounded by design: at most 12 nodes and depth 6.

The DAG is an execution plan, not a second brain. Bitey cognition remains the owner of the objective, constraints, evidence policy, authorization and evaluation. Workers only execute authorized nodes.

Rules:
- unknown dependencies fail closed;
- cycles fail closed;
- node and depth limits are enforced;
- only nodes whose dependencies are completed become ready;
- completed node results can be persisted with the universal task contract;
- external side effects still require authorization;
- paid inference remains forbidden by the task contract.
