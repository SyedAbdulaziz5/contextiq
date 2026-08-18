# Why vector search alone failed

**ContextIQ · engineering note**

Most tutorial RAG stacks ship dense retrieval first: embed the corpus, embed the query, take top‑k. We measured that path on our golden set and it collapsed.

## What we measured

Retrieval experiment on the structural corpus (`docs/eval-results/hybrid-retrieval.json`):

| Mode | Recall@5 | Precision@5 |
|------|----------:|------------:|
| Dense only | **3.9%** | 0.9% |
| Sparse (BM25) | 90.9% | 47.5% |
| Hybrid (dense + sparse → RRF) | 84.9% | 40.0% |
| Hybrid + rerank | **89.3%** | 41.6% |

*Note: this retrieval bake used the local hashing embedder (`local-hashing-1024`) — a weak dense channel by design. It still teaches the right lesson: if your “semantic” path is weak or mismatched, pure vector search is not a product.*

End-to-end RAG on the production-shaped path (structural · hybrid_rerank · extractive) lands **context recall 89.3%** with **faithfulness 100%** (`docs/eval-results/rag-metrics.json`, n=75).

## Why dense alone broke

1. **Keyword-shaped docs** — Lambda limits, Titan model IDs, SST flags: users often ask with exact tokens. Sparse matches them; weak dense embeddings smear them.
2. **Eval before vibes** — Without `eval/golden.jsonl`, “top‑3 looks fine” would have shipped a system that misses ~96% of expected sources at k=5.
3. **Hybrid is not optional** — Combining channels via RRF recovered almost all of the sparse win while keeping a dense path for true paraphrases once embeddings are strong (BGE-small in the free default stack).

## Decision

Production default is **hybrid + rerank**, not dense-only. Sparse alone can win a retrieval bake on this corpus, but the product keeps both channels so we do not regress when questions are semantic rather than lexical.

See also: [ADR 004](../decisions/004-hybrid-retrieval.md) · case study [04 — RRF / rerank](04-rrf-rerank-measured.md).

## Sources

- `docs/eval-results/hybrid-retrieval.json`
- `docs/eval-results/rag-metrics.json`
- `docs/eval-results.md`
