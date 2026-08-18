# ADR 009 — CI-gated RAG quality

## Status

Accepted (Phase 9)

## Context

RAG systems regress silently: a chunking tweak or prompt change can tank recall/faithfulness while unit tests stay green. Recruiters and hiring managers notice when quality is enforced in CI.

## Decision

1. **Separate workflows:** `ci.yml` (lint/typecheck/tests) and `eval.yml` (RAG gate).
2. **Committed baseline** at `eval/ci/baseline.json` representing `main`.
3. **Thresholds** with absolute floors + max regression deltas.
4. **`contextiq-eval gate`** compares `docs/eval-results/rag-metrics.json` to baseline, writes a markdown report, exits non-zero on failure.
5. **PR comment** posts the same report (upserted) so reviewers see the diff without opening logs.
6. **Promote baseline** explicitly after intentional quality changes land on main.

## Consequences

- Contributors must refresh eval JSON when changing retrieval/generation.
- Full offline corpus eval still runs locally (`contextiq-eval run`); CI judges the published scores so we don’t need Bedrock/Postgres secrets for every PR.
- False confidence from extractive faithfulness≈100% is documented; floors still catch recall/refusal collapses.
