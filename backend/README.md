# Bitey IA Web — Cognitive Core Backend

This backend is the server-side foundation of **Bitey IA Web**, the general/integral Bitey IA. It is intentionally independent from BiteFixes CRM/SaaS and from any individual AI model.

## Role

Bitey IA Web is a general-purpose cognitive system. It can coordinate specialized modules, external models, local models, research and tools, while keeping its own cognitive loop and policies.

```text
                 BITEY IA WEB
             GENERAL / INTEGRAL AI
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
    Cognitive        Tools         Modules
      Core          Registry       Registry
       │              │              │
       └──────────────┼──────────────┘
                      ▼
               Supabase/Postgres
```

## Independent cognition

The backend owns:

- context and intent processing;
- Bitey Brain executive routing;
- task decomposition and planning;
- memory selection;
- research/evidence orchestration;
- tool selection and permission policy;
- provider/model selection;
- evaluation, contradiction and confidence controls;
- bounded learning observations.

Models are replaceable inference workers. Bitey must retain a deterministic operating core when no model is available.

## Free-only provider policy

Default policy:

```text
BITEY_COST_MODE=free_only
BITEY_FREE_ONLY_HARD_STOP=true
```

Rules:

1. Only verified free model routes may be selected in free mode.
2. Paid fallback is forbidden.
3. Local/open-weight inference is preferred when available.
4. If no free model is available, deterministic tools or local capabilities continue where possible.
5. Third-party free quotas are not assumed to be unlimited.

No Gemini API is required.

## Memory and knowledge

**Supabase/Postgres is the canonical persistent layer.** PostgreSQL/pgvector can provide semantic retrieval without introducing another database platform.

Neo4j and MongoDB are intentionally excluded from the current Bitey IA Web architecture.

```text
Working context
      ↓
Cognitive Memory
      ↓
Supabase/Postgres
      └── pgvector when enabled
```

## Tool system

Tools are first-class capabilities with explicit contracts. A future Tool Factory may create new deterministic/API tools from task requirements, but every tool must pass schema, permission, risk, cost and resource validation before registration.

```text
Need → Specification → Validation → Implementation → Tests → Registry → Authorized execution → Evaluation
```

Arbitrary model-generated shell/code execution is disabled by default.

## Specialized modules

- **JobIA:** employment intelligence capability.
- **Bitey SBT:** trading intelligence capability with its own risk authority; trading execution remains isolated.
- **Other modules:** can be added through versioned capability contracts.

### BiteFixes boundary

BiteFixes owns its CRM, SaaS and AI-agent implementation. Its **Bitey IA Empresarial** is contextual to each enterprise deployment. It is not absorbed into this general Bitey IA Web backend.

## API surface

Core endpoints include:

- `GET /health`
- `GET /api/v1/capabilities`
- `GET /api/v1/cognitive/status`
- conversation/message APIs

Status endpoints should expose architecture and policy state without exposing secrets.

## Security

- Provider credentials are server-side.
- Model output is untrusted until evaluated.
- Tools require explicit capability permissions.
- Private enterprise context is tenant-scoped.
- Cross-module access uses explicit contracts.
- High-impact actions require stronger authorization.
- Free-only policy is fail-closed.

## Local development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Current phase

The foundation already contains the cognitive core, Brain, memory, learning, evaluation, research, tool orchestration, module registry and provider gateway. The next engineering phase is to harden:

1. free-model discovery and fail-closed routing;
2. Supabase cognitive memory and pgvector retrieval;
3. task-decomposition DAGs;
4. contradiction/confidence/evidence evaluation;
5. permissioned Tool Factory;
6. sandboxed execution for explicitly authorized tools;
7. autonomous recovery from model/tool failures;
8. capability benchmarks and versioned module contracts.

**Invariant:** Bitey IA Web can use other AIs, but it is not dependent on one. It can create/use tools under policy, and the free profile never silently becomes paid.
