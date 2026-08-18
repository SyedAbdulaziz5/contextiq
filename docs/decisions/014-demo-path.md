# ADR 014 — 60-second recruiter demo path

## Status

Accepted

## Context

Recruiters will not reverse-engineer Chat → Eval → Traces. They need a guided path that surfaces grounding, retrieval fusion, evaluation, and refusal in about a minute.

## Decision

1. `/chat?demo=1` enables a **DemoGuide** checklist (5 steps).
2. Preset queries one-click **send** (answerable + unanswerable).
3. Aside shows **Retrieval path** (Dense → Sparse → RRF → Rerank) with highlight for step 3.
4. Step 4 links to `/eval` and marks completion on click.
5. Landing primary CTA: **Try 60s demo** → `/chat?demo=1`.
6. Demo mode is dismissible; can be re-enabled from the chat header strip.

## Consequences

- First-time UX is guided without a heavyweight product tour library.
- Demo queries are fixed corpus questions that match golden-set behavior.

## References

- `apps/web/lib/demo.ts`
