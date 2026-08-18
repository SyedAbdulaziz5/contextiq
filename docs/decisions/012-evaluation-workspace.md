# ADR 012 — Evaluation workspace (current vs baseline)

## Status

Accepted

## Context

Phase 7 shipped metrics + a simple experiment table. Recruiters/engineers still needed an **internal-platform** view: current vs promoted baseline, and per-experiment config (retriever, reranker, top-k, deltas).

## Decision

1. `/eval/dashboard` assembles a **workspace** from:
   - `docs/eval-results/dashboard.json` / `rag-metrics.json` (current)
   - `eval/ci/baseline.json` (previous / main)
   - `docs/eval-results/experiments.json` (full experiment rows)
2. UI shows **Current vs baseline** with percentage-point deltas — never invented numbers.
3. Experiment detail includes chunking, retriever, reranker, top-k, Δ recall (and latency when measured).
4. Production default remains **structural + hybrid_rerank** with an explicit rationale in the payload.
5. Latency averages are recorded on the next `contextiq-eval experiments` / `run` (optional until re-run).

## Consequences

- Eval tab reads as a quality workspace, not a metric dump.
- Promoting baseline (`contextiq-eval promote-baseline`) is what “previous” means in the UI.
- Phase 12 can deepen failed-query analysis on top of this payload.

## References

- `contextiq_ingestion.evaluation.workspace`
