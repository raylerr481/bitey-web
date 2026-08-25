# Bitey Trainer

Bitey Trainer is an **internal capability of Bitey IA**, not a separate product repository.

## Responsibilities

- Evaluate candidate AI responses.
- Build controlled training/improvement plans.
- Identify recurring failure patterns.
- Prepare datasets and ground-truth examples.
- Compare model outputs.
- Propose prompt, routing and knowledge improvements.
- Discover/prepare AI-training opportunities.
- Route tasks that explicitly require a human to the owner for approval.

## Safety boundary

Trainer does not automatically declare an external model response correct. Evaluation is evidence, not truth. Production changes and knowledge promotion require validation.

Trainer also does not automatically accept external paid work, sign contracts, perform identity verification, authorize payments, or impersonate a human. Human-required tasks are surfaced for approval.

## Relationship with BiteFixes

Bitey IA and BiteFixes remain independent projects with independent codebases.

BiteFixes may sell:

1. Bitey IA contextualized for a company's business.
2. Bitey IA Trainer as a professional service for improving a client's AI.

Those commercial services consume Bitey capabilities through explicit authorized API contracts. BiteFixes business data remains isolated by tenant and permission controls.

## Internal flow

```text
Bitey IA
  -> Trainer
      -> evaluate
      -> learn from validated evidence
      -> propose improvement
      -> verify
      -> promote only after approval
```
