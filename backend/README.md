# Bitey IA — Supracerebro Backend

This backend is the server-side foundation of **Bitey IA**, the general-purpose supracerebro behind the Bitey IA web experience.

It is intentionally independent from `bitefixes-backend`.

## Principles

- General-purpose context: no BiteFixes-specific assumptions.
- Dynamic context assembly per conversation, task, research session, user, enterprise, and channel.
- Research is a first-class capability, not a hard-coded provider.
- External AI providers are adapters behind a neutral orchestration layer.
- Enterprise context is optional and scoped; it does not constrain the general brain.
- Memory and knowledge are interfaces so storage can evolve without coupling the core.
- The backend exposes a stable API for the Bitey IA web client and future clients.

## Initial API

- `GET /health`
- `GET /api/v1/capabilities`
- `POST /api/v1/conversations`
- `POST /api/v1/conversations/{conversation_id}/messages`

The current implementation is deliberately provider-neutral. It builds a normalized execution plan and returns a deterministic response when no model provider is configured. Provider integrations can be added without changing the supracerebro contract.

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
