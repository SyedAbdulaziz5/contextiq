# infra/

Deployable ContextIQ stack: **API + web + optional Postgres**.

See **[`docs/runbook-production.md`](../docs/runbook-production.md)** and [ADR 019](../docs/decisions/019-deploy-path.md).

## Compose (API + web)

```bash
# 1) Bake embeddings on the host (gitignored)
cd packages/ingestion && source .venv/bin/activate
contextiq-embed upsert --strategy structural --skip-postgres

# 2) From repo root
docker compose -f infra/docker-compose.yml up --build
```

| Service | URL |
|---------|-----|
| Web | http://localhost:3000 |
| API | http://localhost:8787/health |

Env template: [`compose.env.example`](compose.env.example).

First API image build installs `sentence-transformers` (large download). Default generator is **extractive** (no Ollama in the container).

## Postgres + pgvector (optional)

```bash
docker compose -f infra/docker-compose.yml --profile db up -d db
export DATABASE_URL=postgresql://contextiq:contextiq@localhost:5433/contextiq
# from host venv:
contextiq-embed init-db
contextiq-embed upsert --strategy structural
```

Schema uses **384-d** vectors (BGE-small).

## Free defaults

| Piece | Choice |
|---|---|
| Embeddings | sentence-transformers (BGE-small) — bake + mount |
| LLM | Extractive in Compose · Ollama on host/local path |
| API | `contextiq-serve` container |
| Frontend | Next.js standalone container |

## Files

| File | Role |
|------|------|
| `docker-compose.yml` | api + web + `db` profile |
| `Dockerfile.api` | Python serve (+ local extras in compose) |
| `Dockerfile.web` | Next.js standalone |
| `api-entrypoint.sh` | Warn if embeddings missing |
| `compose.env.example` | Env knobs |

AWS Bedrock / Lambda / SST remain optional — [ADR 010](../docs/decisions/010-free-local-stack.md).
