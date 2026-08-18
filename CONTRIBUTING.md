# Contributing / local development

Short path for humans working on ContextIQ. No process essay.

## Prerequisites

- Python **3.11+**
- Node **20+**
- Optional: [Ollama](https://ollama.com), Docker (Compose stack)

## Setup

```bash
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local

cd packages/ingestion
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[local,serve,dev]'
contextiq-ingest
contextiq-chunk run --strategy structural
contextiq-embed upsert --strategy structural --skip-postgres

cd ../../apps/web && npm install
```

## Day-to-day

| Terminal | Command |
|----------|---------|
| API | `contextiq-serve --port 8787` |
| UI | `cd apps/web && npm run dev` |
| Eval | `contextiq-eval run && contextiq-eval gate` |
| Tests | `cd packages/ingestion && pytest -q` |
| Types | `cd apps/web && npm run typecheck` |

Compose: see [`docs/runbook-production.md`](docs/runbook-production.md).

## Conventions

- Prefer measured changes (re-run eval / update `docs/eval-results` when metrics move).
- Never commit `.env`, keys, or `corpus/embeddings/`.
- ADRs live in `docs/decisions/`.

## PRs

Keep CI green (`.github/workflows/ci.yml` + `eval.yml`). Describe *why* and link any eval delta.
