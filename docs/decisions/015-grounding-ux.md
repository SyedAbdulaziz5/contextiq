# ADR 015 — Grounding / confidence UX

## Status

Accepted

## Context

“Grounded ✔” alone does not explain *why* an answer is trusted, how many sources support it, or when the system refused.

## Decision

1. Every assistant turn shows a **GroundingPanel**:
   - confidence (from pipeline)
   - supporting source count + citation count
   - short summary tied to refusal / confidence
2. **Insufficient evidence** is a distinct refuse state (not a soft badge).
3. Active citation chips highlight matching **claim spans** in the answer text.
4. Optional **weaker neighbors** list uses real similarity / rerank scores only — no invented contradiction scores.
5. Signals come from existing payload fields (`confidence`, `insufficient_context`, `citations`, `sources`, `similarity`, `rerank_score`).

## Consequences

- Grounding is readable without opening Traces.
- Weak-neighbor hints only appear when score gaps are present.

## References

- `apps/web/components/GroundingPanel.tsx`
- `apps/web/lib/grounding.ts`
