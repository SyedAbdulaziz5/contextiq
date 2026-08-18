# ADR 022 — Portfolio story lives outside this repo

## Status

Accepted

## Context

Phase 21 (personal site + resume) is executed outside ContextIQ. Paste-ready copy should not ship in the public product repo.

## Decision

1. Keep resume / homepage drafts local-only (gitignored). Do not add a second Next app here.
2. Public story in this repo is README + `docs/writing/` + `docs/eval-results/`.
3. Live URL is filled in README after hosting.

## Consequences

- Recruiters see the product, metrics, and case studies — not resume drafts.
- Companion projects stay in their own repos, not nested under ContextIQ.

## References

- `docs/writing/README.md`
