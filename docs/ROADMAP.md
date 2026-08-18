# Roadmap & known gaps

ContextIQ (phases 0–19) is in this repo. Remaining work is hosting, publishing, and quality.

## Open

| Item | Status |
|------|--------|
| Public live demo | Local / Compose works; hosted URL not set yet (`docs/DEPLOY.md`) |
| Case-study posts | Drafts in `docs/writing/`; publish ≥2 externally |
| Context precision | ~41.6% — main quality lever still open |

## Known gaps

1. **Public Live Demo URL** — Compose/local works; hosted HTTPS URL not set yet.
2. **Context precision ~41.6%** — Recall/faithfulness/refusal are strong; precision is the main quality lever (chunking / rerank / citation packing).
3. **Multi-tenant auth** — Demo uses open + rate limit or API key; Clerk/Auth.js not wired ([ADR 018](decisions/018-security-model.md)).
4. **Ollama-in-Compose** — Default Compose generator is extractive; fluent LLM needs host Ollama or a separate service.
5. **Distributed rate limiting** — In-memory limiter is single-process; needs Redis (or edge) for multi-replica hosts.
6. **PII scrubbing on traces** — Queries stored as-is for demo observability; scrub before multi-tenant prod.

## Not goals

New RAG clones, Kubernetes-for-show, training LLMs, or swapping every vector database.
