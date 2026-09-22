# Bitey Ecosystem Boundaries

## Purpose

This document is the authoritative boundary map for the Bitey ecosystem. Repositories may integrate through explicit APIs and versioned contracts, but they must not silently share implementation, credentials, deployments, or private domain data.

## Systems

| System | Primary responsibility | Boundary |
|---|---|---|
| Bitey IA Web | General cognitive brain, reasoning, research, memory orchestration, tool routing and coordination | Must not become the business backend of BiteFixes, Enterprise, JobIA or SBT |
| Bitey Enterprise | Business control plane for provisioning/configuring business AI assistants and marketing/growth workflows | Must not become BiteFixes operational backend or duplicate its CRM/ticket system |
| BiteFixes Backend | BiteFixes-specific enterprise AI, CRM/SaaS and operational business APIs | Must remain independent from general Bitey Web and Enterprise implementation |
| Bitey SBT | Trading research, deterministic strategies, simulation, validation, demo/paper and risk-controlled execution | Must not share trading execution authority with the general brain |
| JobIA | Employment/job intelligence and matching | Must remain a bounded specialized capability |

## Non-negotiable isolation

- No repository may copy another system's private credentials.
- No browser client may contain privileged database credentials.
- No system may directly mutate another system's database tables unless an explicit, versioned contract authorizes it.
- Enterprise and BiteFixes are independent systems. Integration, when required, goes through an authenticated backend/API contract.
- Bitey IA Web may coordinate specialized modules, but it does not absorb their domain ownership.
- SBT remains the authority for trading execution and Risk Gate decisions. Bitey IA may propose or delegate; it must not bypass SBT controls.
- BiteFixes remains untouched by normal ecosystem work unless a task explicitly names a BiteFixes change.

## Data architecture

Canonical persistence must be decided per system and per contract. A shared database is not, by itself, permission to share data.

For any cross-system data exchange:

1. Define the owning system.
2. Define the minimum fields exposed by an API contract.
3. Authenticate and authorize the caller.
4. Enforce tenant/domain isolation.
5. Audit the exchange.
6. Do not expose internal tables or service-role credentials to clients.

## Cognitive routing

The intended general flow is:

`Intent → Domain → Capability → Tool → Evidence → Validation → Response`

A specialized result may be normalized by Bitey IA for presentation, but the specialized engine remains authoritative for its domain.

## Evidence and freshness

Bitey IA must distinguish:

- tool failure;
- no evidence;
- conflicting evidence;
- low-confidence evidence;
- verified evidence.

Current/fresh claims must come from tools or retrieved sources, not model-generated text.

## Trading boundary

Trading requests may be delegated to SBT. Bitey IA Web never directly sends broker orders. Demo, paper and live authorization remain inside SBT's deterministic controls and Risk Gate.

## Change rule

When a future task crosses a system boundary, first modify the contract/interface, then the caller/consumer. Never solve cross-system coupling by importing internal modules, sharing secrets, or writing directly into another product's private data layer.
