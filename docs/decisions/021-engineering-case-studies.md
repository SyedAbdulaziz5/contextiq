# ADR 021 — Engineering case studies in-repo

## Status

Accepted

## Context

Portfolio signal comes from judgment under measurement, not feature lists. Drafts must live next to the eval artifacts they cite.

## Decision

1. Case studies live in `docs/writing/` with a short index.
2. Every metric cites a committed path under `docs/eval-results/` or `eval/ci/`.
3. README links the Writing section; publish is MANUAL (LinkedIn / blog / Discussions).
4. When eval numbers change, update affected writeups in the same change set.

## Consequences

- Honest caveats stay in the drafts (e.g. hashing dense bake; extractive faithfulness ceiling).
- “Done” for Phase 20 agent work = five drafts + links; public posts remain on the human.

## References

- `docs/writing/README.md`
