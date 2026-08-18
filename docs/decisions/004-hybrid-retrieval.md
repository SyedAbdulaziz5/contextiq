# ADR 004 — Hybrid retrieval (dense + sparse → RRF → rerank)

**Status:** Accepted  
**Date:** 2026-08-16  
**Phase:** 4

## Context

Pure vector search misses exact tokens (model IDs, error codes, API names). Pure keyword search misses paraphrases. The guide requires both channels, fused with Reciprocal Rank Fusion, then reranked — and measured against the golden set.

## Decision

1. **Dense** top-20 (cosine over embeddings) + **sparse** top-20 (BM25 / same role as `ts_rank`).
2. **Weighted RRF** (`k=60`): equal weights with Bedrock Titan; down-weight dense (`0.35`) when using local hashing so a weak dense channel cannot drown sparse.
3. Fuse to top ~30, then **feature reranker** (term overlap + exact-ID bonuses) → top 5–8.
4. Production CLI default mode: `hybrid_rerank`.
5. Keep modes comparable: `dense | sparse | hybrid | hybrid_rerank` for demos and eval.

## Measured results (structural chunks, local-hashing-1024)

| Mode | Recall@5 | Precision@5 |
|---|---:|---:|
| dense | 0.039 | 0.009 |
| **sparse** | **0.909** | **0.475** |
| hybrid (RRF) | 0.849 | 0.400 |
| **hybrid_rerank** | **0.893** | 0.416 |

### Demo behavior (why hybrid exists)

| Query type | Dense | Sparse | Hybrid+rerank |
|---|---|---|---|
| Exact ID `amazon.titan-embed-text-v2:0` | miss | hit | hit |
| `useSearchParams` (Next.js) | miss | hit | hit |
| Paraphrase / meaning | weak locally | strong on keywords | recovers via sparse + rerank |

**Interview line:** Dense alone fails on exact IDs with a weak embedder; sparse nails keywords; hybrid+rerank keeps the architecture that will improve further when Titan dense quality rises, without giving up keyword wins.

## Consequences

- `contextiq-retrieve {search,compare,eval,demo}`
- Numbers in `docs/eval-results/hybrid-retrieval.json`
- Swap FeatureReranker for Cohere / cross-encoder later without changing the pipeline shape
- With Bedrock Titan, re-run eval — expect dense and hybrid to climb; keep sparse as a safety net

## Alternatives rejected

| Alternative | Why not |
|---|---|
| Dense-only | Fails exact IDs / error codes |
| Sparse-only | Misses paraphrases once embeddings are strong |
| Unweighted RRF + weak dense | Pollutes rankings (we measured this) |
| LangChain retriever chains | Hides RRF/rerank decisions we want to own |
