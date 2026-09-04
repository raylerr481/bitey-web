# Bitey IA Web — General Integral AI Workspace

`bitey-web` is **Bitey IA**, the general/integral AI workspace of the ecosystem. The target is a free-first AI environment with a ChatGPT-like conversation experience and a Skywork-class unified workbench. Skywork is used only as a functional benchmark, never as a dependency. Its official feature surface currently spans General, Images, Documents, Slides, Sheets, Websites, Videos and additional workspace tools. citeturn0search0turn0search1

## Unified workspace surface

The Bitey IA web shell now exposes a single capability hub and dedicated workspace buttons for:

- General Chat
- Deep Research
- Documents
- Slides / presentations
- Sheets / data analysis
- Images / visual creation
- Websites / apps
- AI Developer
- Video
- Audio / Podcast
- Skills / reusable capabilities
- Automations / workflows
- Live Markets / Bitey System Bots Trading
- Projects, Library, conversation history, memory, personalization and settings

The interface is deliberately similar in **functional organization** to modern AI workspaces: one conversation can become research, a document, a presentation, data analysis, a visual asset, a website/app or a bounded workflow. It is not intended to copy Skywork's proprietary implementation or branding.

Skywork's own documentation confirms the unified workspace model and its General, Images, Documents, Slides, Sheets, Websites and Videos feature areas. citeturn0search0

## Product principle

Bitey must behave as a **complete AI**, not as a thin wrapper around another model.

> **Bitey thinks, plans, acts, verifies and learns. Other AIs are replaceable tools.**

The Brain decides what capability is needed. Skills, local models, free-compatible providers and specialized modules are workers/capabilities. The user-facing web environment remains Bitey IA.

## Free-first contract

- deterministic/local capabilities first;
- Ollama/local open-weight inference when available;
- free-compatible providers only when explicitly admitted by policy;
- no silent paid fallback;
- open-source/free libraries for generated artifacts where possible;
- visible quotas and bounded execution;
- graceful degradation when providers disappear;
- no mandatory Skywork, Gemini, MongoDB or Neo4j dependency.

Free-first does not mean unlimited third-party quotas. Bitey remains useful with native/deterministic capabilities when external inference is unavailable.

## Cognitive architecture

```text
User goal
   ↓
Bitey IA Web
   ↓
Perception → Native cognitive substrate → Bitey Brain
                                      ↓
                           capability / skill decision
                                      ↓
          ┌───────────────┬───────────┬───────────────┐
          ↓               ↓           ↓               ↓
       Research        Documents    Data           Markets
          ↓               ↓           ↓               ↓
       Slides          Images      Websites       SBT Live
          ↓               ↓           ↓               ↓
                    execution / inference workers
                                      ↓
                              evaluation / verify
                                      ↓
                         response / artifact / action
```

The native neural substrate is a software cognitive architecture, not a claim of human consciousness.

## Workspace behavior

### General
ChatGPT-like conversation, history, project context, files, voice input, activity indicators and multimodal attachment entry points.

### Deep Research
Bounded multi-step research with source provenance, evidence collection, deduplication and explicit stopping conditions.

### Documents
Markdown/HTML first, with open/free generation paths for DOCX/PDF and research reports.

### Slides
Presentation planning, structured slide generation, speaker notes, charts and PPTX export through pluggable/open tooling.

### Sheets
CSV/XLSX ingestion, formulas, transformations, Python-assisted analysis, charts and export.

### Images
Provider-independent image generation/editing adapters, prioritizing local/open tooling where feasible.

### Websites / Apps
Natural-language requirements → architecture → files → implementation → tests → preview → explicit deployment.

### AI Developer
Repository inspection, coding, tests, debugging, documentation and bounded execution with explicit authorization for high-impact actions.

### Video / Audio
Workspace entry points for scripts, storyboards, audio/podcast structures and pluggable media generation. Media providers remain optional workers.

### Skills
A capability registry for reusable workflows such as research, documents, presentations, spreadsheets, design, development, market intelligence and automation. Skills are capability contracts, not independent brains.

### Automations
Bounded scheduled or event-driven workflows with budgets, permissions, timeouts and stop conditions.

### Live Markets
Bitey IA can open and later consume structured live market intelligence from **Bitey System Bots Trading**. Market observation and analysis are separated from trading execution. Execution remains subject to SBT risk controls.

## Persistent projects

Projects should contain conversations, files, artifacts, research evidence, instructions, memories, skills, task history, provenance and versions. Supabase/PostgreSQL remains the canonical persistence and knowledge layer, with pgvector where enabled.

## Benchmark and inspiration

Skywork and ChatGPT are functional benchmarks only. Skywork also publishes an open-source skills collection covering document, PPT, Excel, design and search/deep-research capabilities; Bitey may learn from public patterns and open standards, but its runtime remains independently controlled. citeturn0search3turn0search5

## Current implementation status

- Native cognitive neural substrate: implemented on feature branch.
- Bounded `MultiStepResearchRuntime`: implemented on feature branch.
- Unified workspace capability hub: implemented on feature branch.
- Live Markets entry point to Bitey SBT: implemented on feature branch.
- Full artifact engines (DOCX/PDF/PPTX/XLSX/media), sandboxed developer execution, persistent Supabase workspace data and autonomous task graphs: next implementation layers.

## Boundaries

`bitey-ai` remains the WordPress plugin/integration. BiteFixes CRM/SaaS remains separate and protected. JobIA and Bitey SBT remain modular specialized systems. MongoDB and Neo4j are not architecture dependencies.

## Roadmap

1. Complete the workspace shell and responsive UX.
2. Integrate the cognitive loop with bounded research.
3. Persist projects, messages, files and artifacts in Supabase.
4. Build document, slide and spreadsheet engines using free/open libraries.
5. Add multimodal image/video/audio adapters.
6. Build AI Developer sandbox and repository workflows.
7. Add skill registry and bounded agent/task graphs.
8. Integrate structured live market context from SBT.
9. Add evaluation, recovery, provenance and contradiction detection.
10. Progressively reduce dependence on external inference.

## Core invariant

**Bitey IA is the AI. The Brain is its cognitive control system. Models, tools and specialized modules are workers/capabilities that Bitey can use, replace, combine or do without.**
