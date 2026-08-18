# Why RRF and rerank improved retrieval

**ContextIQ · engineering note**

Hybrid retrieval without fusion is two ranked lists. Reciprocal Rank Fusion (RRF) merges them; a light reranker reshapes the top of the list. We measured both steps on the same golden answerable set.

## Measured deltas

From `docs/eval-results/hybrid-retrieval.json` (structural corpus, hashing dense channel, n=64 answerable):

| Mode | Recall@5 | Δ vs dense | Δ vs hybrid |
|------|----------:|-----------:|------------:|
| Dense | 3.9% | — | — |
| Hybrid (RRF) | 84.9% | **+81.0 pp** | — |
| Hybrid + rerank | **89.3%** | +85.4 pp | **+4.4 pp** |
| Sparse alone | 90.9% | — | — |

Rerank also lifts **precision@5** from 40.0% (hybrid) to **41.6%** (hybrid_rerank) — small but same direction as the end-to-end context precision in `rag-metrics.json` (**41.6%**).

Chunking experiments (sparse BM25 only, `docs/eval-results/experiments.json`) show structural vs semantic:

| Setup | Recall | Faithfulness |
|-------|-------:|-------------:|
| Structural chunks | 90.9% | 100% |
| Semantic chunks | 80.2% | 100% |
| Hybrid + reranker (prod-shaped) | 89.3% | 100% |

Semantic chunking lost **~10.7 pp** recall vs structural on that bake. Production default stays **structural + hybrid_rerank** even when sparse-only “wins” a single table — we want dense paraphrases when embeddings are strong (BGE-small), not a BM25 monoculture.

## What RRF buys

- Dense and sparse disagree; RRF rewards items that rank well on either list without score-scale fights.
- When dense is weak (hash experiment), RRF still lets sparse dominate instead of averaging into garbage.

## What rerank buys

- +4.4 pp recall@5 on this bake after fusion.
- Better packing of the top‑5 that the generator actually sees (precision nudge).

## Decision

Keep **dense + sparse → RRF → rerank** as the serving path. Do not ship dense-only. Treat sparse-only as a strong ablation, not the product architecture.

See: [ADR 004](../decisions/004-hybrid-retrieval.md) · [01 — vector alone](01-vector-search-alone-failed.md).

## Sources

- `docs/eval-results/hybrid-retrieval.json`
- `docs/eval-results/experiments.json`
- `docs/eval-results/rag-metrics.json`
