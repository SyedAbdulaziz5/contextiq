# ADR 003 — Postgres + pgvector + local/Bedrock embeddings

**Status:** Accepted  
**Date:** 2026-08-16  
**Phase:** 3

## Context

Phase 3 needs a real semantic retrieval layer: chunks → embeddings → vectors → searchable store. The project guide specifies **PostgreSQL + pgvector** (dense) alongside native **tsvector** (sparse) so hybrid retrieval (Phase 4) lives in one database — no Pinecone/LangChain abstraction.

## Decision

1. **Schema:** `documents` + `chunks` with `embedding VECTOR(1024)`, generated `content_tsv`, HNSW cosine index, GIN tsvector index (`packages/ingestion/sql/001_schema.sql`).
2. **Production embedder:** Amazon Titan Text Embeddings V2 on Bedrock (`amazon.titan-embed-text-v2:0`, 1024-d, `normalize=true`), with explicit throttling retries.
3. **Local embedder:** deterministic 1024-d feature hashing for offline plumbing/CI when AWS is unavailable. Same vector width as Titan so the schema does not change.
4. **Dual write path:** always write `corpus/embeddings/{strategy}/embeddings.jsonl`; upsert into Postgres when `DATABASE_URL` is set.
5. **Own the SQL:** dense search via `embedding <=> query` (cosine distance); sparse via `ts_rank_cd` / `plainto_tsquery`. No LangChain vector stores.
6. **Default chunk strategy for upsert:** `structural` (Phase 2 ADR).

## Consequences

**Positive**
- One DB for dense + keyword (Phase 4 RRF is a query change, not a vendor change).
- Interviewable: cosine distance vs similarity, HNSW, metadata filters, tsvector.
- Works offline for learning the pipeline; Bedrock swap is an env flag.

**Tradeoffs**
- Local hashing has **poor** semantic recall (measured ~0.06–0.20 Source Recall@5). That is intentional honesty — it proves plumbing, not quality.
- Requires Docker (or any Postgres with `pgvector`) for the real store.
- Bedrock needs AWS credentials and incurs cost/rate limits.

## Alternatives rejected

| Alternative | Why not |
|---|---|
| Pinecone / Chroma | Extra vendor; weaker “one DB hybrid” story |
| LangChain vector wrappers | Hides the SQL we want to own |
| 384-d MiniLM in schema | Diverges from Titan 1024-d production path |
| Skip local provider | Blocks Phase 3 without AWS keys |
