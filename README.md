# ContextIQ

**Eval-first RAG for production knowledge & support systems.**

Hybrid retrieval · grounded citations · refusal · traces · CI quality gate — **free / local by default**.

[Live Demo](https://contextiq.vercel.app) · [Architecture](docs/architecture.md) · [Evaluation](docs/eval-results.md) · [Writing](docs/writing/README.md) · [Deploy](docs/DEPLOY.md)

> **Live demo:** update the URL above once deployed. Until then, run locally with the quick-start below.

[![CI](https://github.com/YOUR_GITHUB_USERNAME/RAG_system/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_GITHUB_USERNAME/RAG_system/actions/workflows/ci.yml)
[![RAG Eval](https://github.com/YOUR_GITHUB_USERNAME/RAG_system/actions/workflows/eval.yml/badge.svg)](https://github.com/YOUR_GITHUB_USERNAME/RAG_system/actions/workflows/eval.yml)

| Context recall | Faithfulness | Refusal accuracy | Hallucination |
|---------------:|-------------:|-----------------:|--------------:|
| **89.3%** | **100%** | **100%** | **0%** |

From [`docs/eval-results/rag-metrics.json`](docs/eval-results/rag-metrics.json) — structural · hybrid_rerank · extractive (`n=75`). Full writeup: [`docs/eval-results.md`](docs/eval-results.md).

## Why not another chatbot

| Tutorial RAG | ContextIQ |
|---|---|
| Build first, eyeball later | Golden set + CI gate before "ship" |
| Vector-only | Dense + sparse → RRF → rerank |
| Answers without sources | Citations + refuse when ungrounded |
| No regression story | Measured baselines in `eval/ci/` |

## Stack

| Layer | Default (free) | Optional |
|---|---|---|
| UI | Next.js (`apps/web`) | Vercel |
| API | `contextiq-serve` (Starlette SSE) | FastAPI-shaped later |
| Embeddings | BGE-small via sentence-transformers | Bedrock Titan |
| LLM | Ollama · extractive fallback | Bedrock Haiku |
| Store | Embedding cache · optional pgvector | Managed Postgres |
| Deploy | Local → Compose → Vercel + Railway | — |

## Repository

```
RAG_system/
├── apps/web/              # Next.js: landing, chat, eval, traces
├── packages/ingestion/    # Python: ingest → retrieve → generate → eval → serve
├── infra/                 # docker-compose: api + web + optional Postgres
├── corpus/                # sources.json (+ gitignored raw/chunks/embeddings)
├── eval/                  # golden.jsonl + CI baseline/thresholds
├── docs/                  # architecture, ADRs, eval results, writing, deploy
└── .github/workflows/     # ci.yml · eval.yml · deploy.yml
```

## Local development

```bash
# 1. Python env
cd packages/ingestion
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[local,serve,dev]'

# 2. Ingest, chunk, embed (one-time — downloads ~130MB BGE model)
contextiq-ingest
contextiq-chunk run --strategy structural
contextiq-embed upsert --strategy structural --skip-postgres

# 3. Optional fluent LLM (answers still work without it via extractive)
# brew install ollama && ollama pull llama3.2:1b

# 4. API
export CONTEXTIQ_EMBEDDING_PROVIDER=sbert
export CONTEXTIQ_GENERATOR=extractive
contextiq-serve --host 127.0.0.1 --port 8787

# 5. UI (second terminal)
cd apps/web && npm install && npm run dev
# Open: http://localhost:3000
```

Compose (after embed bake):

```bash
docker compose -f infra/docker-compose.yml up --build
```

Env templates: [`.env.example`](.env.example) · [`apps/web/.env.example`](apps/web/.env.example). More: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Deploy to Vercel + Railway/Render

See **[`docs/DEPLOY.md`](docs/DEPLOY.md)** for step-by-step.

Short version:
1. Push this repo to GitHub.
2. Deploy **`apps/web`** to Vercel — set `NEXT_PUBLIC_API_URL` to your API host.
3. Deploy **`contextiq-serve`** to Railway/Render using `infra/Dockerfile.api`.
4. Set `CONTEXTIQ_CORS_ORIGINS` on the API to allow your Vercel domain.

## Quality gate

```bash
cd packages/ingestion && source .venv/bin/activate
contextiq-eval run && contextiq-eval gate
```

## Writing

Engineering notes (all metrics from committed eval JSON):

1. [Why vector search alone failed](docs/writing/01-vector-search-alone-failed.md)
2. [Knowing when not to answer](docs/writing/02-knowing-when-not-to-answer.md)
3. [RAG regression CI gate](docs/writing/03-rag-regression-ci-gate.md)
4. [RRF / rerank measured](docs/writing/04-rrf-rerank-measured.md)
5. [Offline / local stack](docs/writing/05-offline-local-stack.md)

## Docs map

| Doc | Purpose |
|-----|---------|
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Vercel + Railway/Render deploy guide |
| [`docs/architecture.md`](docs/architecture.md) | Pipeline + Local→Compose→Hosted |
| [`docs/eval-results.md`](docs/eval-results.md) | Headline metrics |
| [`docs/security.md`](docs/security.md) | Auth / rate limits / injection |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Known gaps |
| [`docs/VERIFY-AND-START.md`](docs/VERIFY-AND-START.md) | Full local start + test guide |

## License

MIT — see [LICENSE](LICENSE).
