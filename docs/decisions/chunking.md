# ADR 002 — Chunking strategy comparison (Phase 2)

**Status:** Accepted  
**Date:** 2026-08-14  
**Phase:** 2

## Context

Chunking is a retrieval hyperparameter. Picking `500 / 50` from a blog is not an engineering decision. We implemented three strategies, ran them against `eval/golden.jsonl`, and measured **source-level Context Recall@k** with BM25 over chunks (lexical retrieval proxy before Phase 3/4 dense+hybrid).

Raw numbers: `docs/eval-results/chunking-comparison.json` (full corpus distractors) and `chunking-comparison-aws-only.json`.

## Strategies

| Strategy | Approach |
|---|---|
| **fixed** | Flatten doc → 500 whitespace-tokens, 15% overlap. No structure. |
| **structural** | Headings → blocks → sentences. Tables/code **atomic**. Merge small pieces. |
| **semantic** | Sentence/block units; split on local TF-IDF cosine drop (+ max/min token guards). |

## Results (full corpus, BM25 Source Recall)

| Strategy | Chunks | Avg tokens | Recall@5 | Recall@10 |
|---|---:|---:|---:|---:|
| **fixed** | 223 | 436 | **0.9115** | 0.9271 |
| **structural** | 209 | 409 | 0.9089 | **0.9323** |
| **semantic** | 729 | 117 | 0.8021 | 0.9036 |

### Category highlights (full corpus)

| Category | fixed@5 | structural@5 | semantic@5 |
|---|---:|---:|---:|
| factual | 1.00 | 1.00 | 1.00 |
| table | 1.00 | 1.00 | 0.94 |
| keyword | 0.91 | 0.91 | 0.64 |
| multi_hop | 0.73 | 0.71 | 0.73 |

## Decision

**Production default: `structural`.**

Not because it crushed Recall@5 (it is statistically tied with fixed), but because:

1. **Recall@10 is best** (0.9323) — more room for rerankers later.
2. **Citation metadata** — every chunk carries `section_title`, `heading_path`, `section_id`.
3. **Table integrity** — quota tables stay intact instead of being sliced mid-row by fixed windows.
4. **Semantic (TF-IDF) underperformed** — over-fragmentation hurt keyword@5; revisit boundaries with Bedrock Titan embeddings in Phase 3 before promoting semantic.

Fixed remains the **baseline** in CI for regression diffs.

## Consequences

- Chunk artifacts: `corpus/chunks/{fixed,structural,semantic}/chunks.jsonl`
- Downstream embedding/retrieval should load **structural** by default.
- Re-run: `contextiq-chunk lab`

## Alternatives rejected

| Alternative | Why not |
|---|---|
| Ship fixed-only | Loses structure needed for citations/tables |
| Ship semantic-now | Worse recall; TF-IDF ≠ production embeddings |
| Skip measurement | Exactly the weak portfolio pattern we are avoiding |
