# ADR 020 — GitHub packaging

## Status

Accepted

## Context

Recruiters and engineers judge a repo from the README first. Metrics must be real; structure must match what is in the tree.

## Decision

1. README hero links: Live Demo (local/runbook until hosted) · Architecture · Evaluation · Roadmap.
2. Metric strip quotes committed `docs/eval-results/rag-metrics.json` only — never invented numbers.
3. Repo tree called out in README: `apps/`, `packages/`, `infra/`, `corpus/`, `eval/`, `docs/`, `.github/`.
4. `CONTRIBUTING.md` = local development only (short).
5. `docs/ROADMAP.md` lists known gaps as issue-shaped bullets for when Issues are opened.

## Consequences

- After hosting, replace the Live Demo placeholder with the public HTTPS URL.
- When eval numbers change, update README strip + `docs/eval-results.md` together.

## References

- `docs/ROADMAP.md`
