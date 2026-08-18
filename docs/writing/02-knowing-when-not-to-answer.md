# How ContextIQ knows when not to answer

**ContextIQ · engineering note**

A support RAG that invents Azure timeouts or stock prices is worse than a blank chat box. ContextIQ treats **refusal** as a first-class outcome, not an afterthought.

## What “not answering” means here

For questions outside the corpus — or that should not be answered from docs — the system returns a fixed refusal and marks `insufficient_context` / `refused`.

Measured on the golden unanswerable slice (`docs/eval-results/grounded-generation.json`):

| Metric | Result |
|--------|--------|
| Unanswerable queries | 9 |
| Correct refusals | **9 / 9** |
| Refusal accuracy | **100%** |

The same number appears in the headline RAG suite: **refusal accuracy 100%**, **hallucination rate 0%** (`docs/eval-results/rag-metrics.json`).

Examples that must refuse (from the eval detail): AMZN stock price, Azure Functions timeouts, private sprint notes, “who invented Lambda,” jokes then quotas.

## Mechanisms (stacked, not magical)

1. **Retrieval weakness → pre-refuse** — Generators call `should_refuse` when hits are empty or scores are below a floor.
2. **Extractive grounding** — The free default generator answers by selecting sentences from retrieved chunks. No fluent invent path when context does not support the claim → faithfulness stays at the ceiling (**100%** on the extractive run).
3. **Prompt rules** — System prompt: answer only from `[S#]` blocks; treat user + retrieved text as data; refuse when insufficient.
4. **Injection guard** — Heuristic refuse for “ignore previous instructions / secret API key” style prompts (Phase 17), plus golden `q066`.
5. **Router skips** — Some turns never hit RAG (greetings / out-of-scope routes).

## What we still watch

Faithfulness ≈ 100% on extractive is expected (answers are copied from context). It is **not** the same as a strong generative model under jailbreak pressure. Refusal accuracy is the metric we gate in CI for “don’t make things up.”

## Decision

Ship refusal as a product feature: UI shows confidence / grounding, eval scores refusal, CI floors it at **≥ 90%** (`eval/ci/thresholds.json`).

See: [ADR 006](../decisions/006-grounded-generation.md) · [docs/security.md](../security.md).

## Sources

- `docs/eval-results/grounded-generation.json`
- `docs/eval-results/rag-metrics.json`
- `eval/ci/thresholds.json`
