# ADR 019 — Deploy path (Local → Compose → Hosted)

## Status

Accepted

## Context

A portfolio RAG that only runs in a laptop venv is hard to trust as “production-shaped.” We need a documented path to containers and a hook for real hosting without forcing one vendor.

## Decision

1. **Three stages:** Local (venv) → Compose (`infra/docker-compose.yml`: api + web + optional db) → Hosted (operator’s choice).
2. **Bake embeddings outside the image** — `corpus/embeddings` stays gitignored; mount or copy into the API at run time. Image installs `serve,local` so query embeddings match BGE cache.
3. **Compose defaults:** extractive generator, open auth + rate limits, CORS to localhost web. Ollama/Postgres are optional.
4. **GitHub `deploy.yml`:** validate docs + compose config + optional smoke API image build; real promote is MANUAL (secrets + host account).
5. **Eval gate before promote** — same CI gate as merge; documented in the runbook.

## Consequences

- First Compose build downloads torch/sentence-transformers (slow, expected).
- Live public URL remains a human step (billing/DNS).
- Vercel-only frontends must set `NEXT_PUBLIC_API_URL` to the public API origin.

## References

- `docs/runbook-production.md`
- `docs/DEPLOY.md`
- `infra/README.md`
