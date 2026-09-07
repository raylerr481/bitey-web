# Bitey IA capability routing

## Responsibility boundary

Bitey IA is the general intelligence/orchestrator. Specialized domains remain authoritative in their own products:

- `jobia`: employment, jobs, profiles, applications and work-domain workflows.
- `sbt`: trading research, strategy design, simulation, validation, demo/paper and risk-controlled execution workflows.
- `general`: normal conversation and general reasoning in Bitey Core.

## Routing contract

The router is deterministic and runs before delegation. A delegated request carries `X-Bitey-Capability: jobia` or `X-Bitey-Capability: sbt`. If that header is already present, the router does not delegate again, preventing recursive loops.

Specialized modules return their own domain result. Bitey IA may normalize the result into its public response contract, but must not duplicate the specialized engine.

## Trading safety boundary

Bitey IA never bypasses SBT's deterministic engine or Risk Gate. A trading request can be delegated to SBT, but authorization for demo, paper or live actions remains an SBT responsibility. The router itself has no broker execution capability.

## Current integration status

The classifier and loop-prevention contract are implemented and unit-tested. Endpoint-level delegation is intentionally separate from classification so the actual JobIA and SBT URLs/contracts can be configured explicitly rather than silently guessing or introducing paid services.
