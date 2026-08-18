# ADR 005 — Query understanding (route → rewrite → optional HyDE)

**Status:** Accepted  
**Date:** 2026-08-16  
**Phase:** 5

## Context

Raw user text is often a bad retrieval query: greetings waste retrieval, follow-ups lack entities, and complex questions may embed poorly. The guide requires **routing**, **rewriting**, and **HyDE**, with **tests** rather than assumed winners.

## Decision

1. **Router (deterministic):** `greeting | meta | calculation | clarification | rag`. Non-RAG routes skip retrieval.
2. **Rewriter (deterministic):** resolve follow-ups / pronouns using prior user turns into a standalone question.
3. **HyDE (pluggable):** `template` offline stand-in + optional `bedrock` LLM HyDE. Dense channel may embed the hypothetical doc; sparse always uses the rewritten question.
4. **Measure:** router/rewriter fixture accuracy + A/B `raw` vs `hyde` dense on golden Recall@5.

## Measured results

| Check | Result |
|---|---|
| Router fixtures | **1.00** accuracy |
| Rewriter fixtures | **1.00** accuracy |
| HyDE A/B (template, local embeds, hybrid_rerank) | raw Recall@5 **0.893** vs hyde **0.878** → **raw_better** (Δ −0.016) |

**Conclusion:** Do **not** enable template HyDE by default. Keep HyDE as an opt-in experiment; re-test with Bedrock HyDE + Titan embeddings before promoting it.

Default ask path: `route → rewrite → dense_strategy=raw → hybrid_rerank`.

## Consequences

- `contextiq-query {route,rewrite,hyde,ask,ab-hyde,eval}`
- Numbers: `docs/eval-results/query-understanding.json`
- Follow-up demo: history “Server Components” + “what about the second one?” → rewritten to limitations query → retrieves `nextjs-server-and-client-components`

## Alternatives rejected

| Alternative | Why not |
|---|---|
| Always retrieve | Burns cost on “hi” / meta |
| Always HyDE | Measured regression with template HyDE |
| LLM-only router without rules | Harder to test offline; rules cover the critical skips |
| Blindly trust a blog on HyDE | Violates the “testing matters” requirement |
