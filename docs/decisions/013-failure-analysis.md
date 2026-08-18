# ADR 013 — Failure analysis as a first-class surface

## Status

Accepted

## Context

Eval dashboards show aggregates. Senior reviewers want to see **how the system fails**, what was retrieved, what should have happened, what was fixed, and **measured** before/after numbers.

## Decision

1. Curated cases live in `docs/eval-results/failure-cases.json` (joined from golden + eval artifacts).
2. UI route `/failures` + API `GET /eval/failures`.
3. Every case includes: question, retrieved, observed vs expected, fix, metric impact with **source path**, lesson.
4. Open vs mitigated status — do not invent “fixed” metrics; open gaps stay open with honest notes.
5. Eval workspace links to Failure analysis (not only a raw failed-id list).

## Consequences

- Portfolio signal: debugging narrative, not vibes.
- Cases must be updated when eval artifacts change (re-seed from real ids).

## References

- `docs/eval-results/failure-cases.json`
