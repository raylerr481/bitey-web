# Bitey IA Web — General Integral AI Workspace

`bitey-web` is **Bitey IA**, the general/integral AI workspace of the ecosystem. The product target is a free-first AI environment with a ChatGPT-like conversational experience and a Skywork-like workbench for research, documents, slides, sheets, images, websites, code and agentic workflows.

Bitey is not the BiteFixes CRM, not BiteFixes SaaS and not the `bitey-ai` WordPress plugin. Those remain separate product boundaries.

## Product vision

Bitey must behave as a **complete AI**, not as a thin wrapper around another model. The user gives Bitey a goal; Bitey understands it, plans it, attempts to solve it with its own cognitive capabilities and tools, and only then recruits external/local AI models when they provide useful inference capabilities.

> **Bitey thinks, plans, acts, verifies and learns. Other AIs are replaceable tools.**

The workspace should make complex work feel as simple as ChatGPT while providing the production-oriented capabilities of an AI office/workspace: deep research with citations, document creation, presentations, spreadsheets/data analysis, image generation/editing, website generation, code assistance, file/project context, reusable skills, and bounded autonomous workflows.

## Free-first contract

The target is **usable without mandatory paid AI APIs**:

- deterministic/local capabilities first;
- Ollama/local open-weight inference when available;
- free-compatible providers only when explicitly admitted by policy;
- no silent paid fallback;
- external models are optional workers;
- generated files should use open-source/free libraries where possible;
- quotas must be visible and bounded;
- graceful degradation when a provider disappears.

Free does not mean unlimited third-party quota. Bitey must remain operational with local/deterministic capabilities even when external free quotas are exhausted.

## Native Bitey cognition

The cognitive substrate belongs to Bitey:

```text
User goal
   ↓
Perception
   ↓
Native cognitive neural substrate
   ↓
Bitey Brain
   ├── understand
   ├── remember
   ├── focus/attention
   ├── decompose
   ├── plan
   ├── choose tools
   ├── decide whether external AI is needed
   ├── evaluate evidence
   ├── verify
   └── learn from outcomes
   ↓
Execution / inference workers
   ↓
Evaluation + verification
   ↓
Final Bitey response / artifact / authorized action
```

The native neural substrate is deliberately not presented as a claim of human-like consciousness. It is a software cognitive architecture: interacting units, state, activation, attention, memory signals, confidence, goals, constraints and bounded learning that Bitey owns independently of any LLM provider.

## AI workspace

The web environment is planned as a single persistent workspace rather than a collection of disconnected chat pages.

### General Chat

ChatGPT-like conversation with:

- streaming responses;
- conversation history;
- multimodal input;
- files and project context;
- citations and source inspection;
- model/tool transparency;
- task progress;
- regeneration and refinement;
- Spanish, Portuguese and English support.

### Deep Research

Bitey Brain decides when research is useful. `MultiStepResearchRuntime` executes bounded research with hard limits on subquestions, passes and sources. Evidence is deduplicated, evaluated and returned to the Brain; research must never become an unlimited LLM loop.

### Documents

Generate, edit, transform and export professional documents using open/free libraries where possible:

- Markdown/HTML;
- DOCX;
- PDF;
- structured reports;
- research reports with citations;
- reusable templates.

### Slides

Create editable presentations from a goal, document or research project:

- outline generation;
- slide planning;
- layouts;
- charts/tables;
- speaker notes;
- PPTX export;
- iterative slide-level refinement.

### Sheets / Data

Provide a spreadsheet/data-analysis workspace:

- CSV/XLSX import;
- formulas;
- transformations;
- Python-based analysis where authorized;
- charts;
- summaries;
- anomaly detection;
- XLSX/CSV export.

### Images and visual generation

Support image generation/editing through pluggable providers, with local/open-source options prioritized when feasible. Provider choice remains controlled by Bitey policy.

### Websites and apps

Bitey should be able to turn a natural-language goal into a structured web project:

```text
idea → requirements → architecture → files → implementation → tests → preview → deploy
```

Deployment must remain permissioned and explicit. Bitey may prepare artifacts without automatically publishing high-impact changes.

### AI Developer

A controlled coding workspace for:

- repository analysis;
- code generation;
- patch proposals;
- tests;
- debugging;
- documentation;
- bounded execution/sandboxing;
- Git workflows through explicit authorization.

### Skills / agents

Bitey will use a capability/skill registry so specialized workflows can be added without replacing the Brain:

```text
Bitey Brain
     ↓
Skill registry
     ↓
Research | Docs | Slides | Sheets | Code | Web | Data | Image | Automation
```

A skill is a capability contract, not another independent brain.

## Persistent projects

Every workspace project should be able to contain:

- conversations;
- uploaded files;
- generated artifacts;
- research evidence;
- instructions;
- memories;
- skills;
- task history;
- provenance;
- versions.

Supabase/PostgreSQL remains the canonical persistent data and knowledge layer, with pgvector where enabled. No MongoDB or Neo4j dependency is part of this architecture.

## Autonomous workflows

Bitey should eventually support bounded long-running tasks:

```text
Goal
 ↓
Plan
 ↓
Task graph
 ↓
Execute
 ↓
Observe
 ↓
Evaluate
 ↓
Correct / continue
 ↓
Complete
```

Autonomy is bounded by budgets, timeouts, permissions, tool policies and stop conditions. High-impact external actions require explicit authorization.

## Model independence

```text
                 BITEY BRAIN
                      │
              capability decision
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
   Native/local   Free providers   Specialized
   inference      when useful      inference
       │              │              │
       └──────────────┼──────────────┘
                      ▼
               Bitey evaluator
```

If a model disappears, Bitey should switch to another eligible worker or degrade to native/deterministic capabilities. No provider becomes the authority over Bitey's decisions.

## Product benchmark

Bitey uses Skywork and ChatGPT as **functional benchmarks**, not architectural dependencies. The target benchmark is a unified workspace spanning conversation, deep research, documents, presentations, spreadsheets, visual creation, web/app creation, developer workflows and reusable skills.

Bitey's goal is not to copy another product's UI. It is to build the underlying experience as an open, free-first system where **Bitey's own cognitive architecture remains in control**.

## Boundaries

### Bitey IA WordPress plugin

`bitey-ai` is the WordPress plugin and user-facing integration/widget. It is not the general Bitey IA Web brain.

### BiteFixes

BiteFixes CRM/SaaS and its existing structure remain separate and protected. Bitey Web can provide capabilities through explicit contracts without absorbing or rewriting BiteFixes.

### Specialized modules

JobIA, Bitey SBT and future modules remain modular. Bitey Brain can route work to them through versioned capability contracts and risk boundaries.

## Roadmap to the Bitey AI Workspace

1. Native cognitive neural substrate and executive Brain.
2. Bounded MultiStepResearchRuntime integrated into the cognitive loop.
3. ChatGPT-like workspace shell and persistent project system.
4. File ingestion, multimodal context and artifact management.
5. Deep Research with provenance, citations and contradiction detection.
6. Documents engine and DOCX/PDF export.
7. Slides engine and PPTX export.
8. Sheets/data engine and XLSX/CSV analytics.
9. Image/visual capability adapters.
10. AI Developer workspace with sandboxed execution.
11. Skills/capability registry and reusable workflows.
12. Bounded agentic task graphs and scheduled jobs.
13. Native evaluation, self-tests, recovery and capability benchmarks.
14. Free-first model discovery, health and fail-closed routing.
15. Progressive reduction of dependency on external inference through Bitey's own cognitive capabilities.

## Core invariant

**Bitey IA is the AI. The Brain is its cognitive control system. Models, tools and specialized modules are workers/capabilities that Bitey can use, replace, combine or do without.**