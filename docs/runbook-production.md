# Production runbook

Operate ContextIQ beyond “works on my laptop.” Companion: [ADR 019](decisions/019-deploy-path.md).

## Paths

| Stage | What | Command / notes |
|-------|------|-----------------|
| **Local** | venv + Next | `contextiq-serve` + `npm run dev` — [SETUP-FREE](SETUP-FREE.md) |
| **Compose** | API + web (+ optional db) | `docker compose -f infra/docker-compose.yml up --build` |
| **Hosted** | Your host | MANUAL: Fly / Railway / Render / Vercel+API — set secrets, HTTPS |

## Bake embeddings (before Compose or promote)

Corpus embeddings are **not** in git (`corpus/embeddings/`). Bake on a machine with the embedder:

```bash
cd packages/ingestion && source .venv/bin/activate
pip install -e '.[local]'
contextiq-embed upsert --strategy structural --skip-postgres
# optional Postgres:
# export DATABASE_URL=postgresql://contextiq:contextiq@localhost:5433/contextiq
# docker compose -f infra/docker-compose.yml --profile db up -d db
# contextiq-embed init-db && contextiq-embed upsert --strategy structural
```

Compose mounts `corpus/embeddings` read-only into the API container. Provider must match the cache (`sbert` for BGE bake).

## Compose stack

```bash
# from repo root
docker compose -f infra/docker-compose.yml up --build
# UI http://localhost:3000 · API http://localhost:8787/health
```

Env: `infra/compose.env.example`. Security knobs: [security.md](security.md).

| Service | Port | Health |
|---------|------|--------|
| `api` | 8787 | `GET /health` → `ok: true` |
| `web` | 3000 | HTTP 200 |
| `db` (profile) | 5433 | `pg_isready` |

Default generator in Compose is **extractive** (no Ollama in the container). Point `CONTEXTIQ_GENERATOR=ollama` only if Ollama is reachable from the API container.

## Eval gate before promote

Do not promote a build that fails the RAG gate:

```bash
cd packages/ingestion && source .venv/bin/activate
CONTEXTIQ_EMBEDDING_PROVIDER=sbert CONTEXTIQ_GENERATOR=extractive \
  contextiq-eval run && contextiq-eval gate
```

CI already runs the gate on PRs (`.github/workflows/eval.yml`). Treat a red gate as a deploy blocker.

## GitHub Deploy workflow

Actions → **Deploy** → `workflow_dispatch`:

| Target | Meaning |
|--------|---------|
| `docs-check` | Eval artifacts present |
| `compose-config` | `docker compose … config` validates |
| `compose-build-smoke` | Builds API image with `PIP_EXTRAS=serve` only (no torch) |
| `note-only` | Reminder in job summary |

Wire a real host by adding a job that uses your provider’s action/CLI and repository secrets (`CONTEXTIQ_API_KEY`, `DATABASE_URL`, etc.). Keep the eval gate green before that job runs.

## Hosted checklist (MANUAL)

1. Pick host (billing account).
2. Create project; set env from `.env.example` + `infra/compose.env.example`.
3. Bake embeddings on a build machine / volume; do not rely on empty `corpus/embeddings` in git.
4. HTTPS + public URL.
5. Put Live Demo URL in README (Phase 19 packaging polish).
6. Optional domain.

## Health / smoke after deploy

```bash
curl -fsS https://YOUR_API/health
curl -fsS -X POST https://YOUR_API/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the Lambda timeout?"}'
# open https://YOUR_WEB/
```
