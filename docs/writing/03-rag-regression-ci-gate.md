# Regression testing for RAG (the CI gate)

**ContextIQ · engineering note**

Unit tests do not notice when chunking or retrieval quietly drops recall. ContextIQ fails the PR when published RAG metrics fall below floors or regress vs `main`.

## Setup

| Piece | Location |
|-------|----------|
| Golden questions | `eval/golden.jsonl` |
| Published scores | `docs/eval-results/rag-metrics.json` |
| Baseline (`main`) | `eval/ci/baseline.json` |
| Floors + max drop | `eval/ci/thresholds.json` |
| Workflow | `.github/workflows/eval.yml` |
| CLI | `contextiq-eval run` · `contextiq-eval gate` |

Absolute floors (fractions):

| Metric | Floor |
|--------|------:|
| Context recall | 0.85 |
| Faithfulness | 0.90 |
| Refusal accuracy | 0.90 |
| Context precision | 0.30 |
| Answer relevancy | 0.50 |

Max regression vs baseline is also capped (e.g. recall ≤ 3 pp drop). See `eval/ci/thresholds.json`.

## Why this shape

1. **CI does not need Bedrock** — Gate judges committed JSON so every PR stays free/offline.
2. **Two workflows** — `ci.yml` for lint/tests; `eval.yml` for RAG. Green unit tests cannot hide a recall cliff.
3. **Promote deliberately** — After an intentional quality change, refresh eval JSON and update the baseline.

## Current bar (committed)

From `docs/eval-results.md` / `rag-metrics.json` (structural · hybrid_rerank · extractive, n=75):

- Context recall **89.3%**
- Faithfulness **100%**
- Refusal accuracy **100%**
- Context precision **41.6%** (above the 30% floor; still the main open quality lever)

## Decision

Quality is a merge requirement, not a dashboard screenshot. If you change retrieval or generation, re-run eval and keep the gate green.

See: [ADR 009](../decisions/009-ci-eval-gate.md) · [ADR 007](../decisions/007-rag-evaluation.md).

## Sources

- `eval/ci/thresholds.json`
- `docs/eval-results/rag-metrics.json`
- `docs/decisions/009-ci-eval-gate.md`
