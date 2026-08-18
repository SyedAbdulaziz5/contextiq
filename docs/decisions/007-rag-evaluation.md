# ADR 007 — Measure RAG quality with first-party metrics

## Status

Accepted (Phase 7)

## Context

Portfolio RAG projects often claim “citations” and “no hallucinations” without numbers. Phase 7 must produce **reproducible evidence** on the golden set.

## Decision

1. **Implement metrics ourselves** (precision, recall, faithfulness, relevancy, refusal) so we own the definitions — not only wrap RAGAS.
2. **Faithfulness via claim–context overlap** offline (Bedrock judge optional later); refusals count as faithful.
3. **Experiment matrix** comparing chunk strategies (BM25) vs hybrid+rerank on Recall × Faithfulness.
4. **Publish** `docs/eval-results.md` + JSON + `/eval` dashboard for GitHub/recruiters.
5. **CI** gates unit tests for metric correctness; full suite runs locally against gitignored corpus caches.

## Consequences

- Scores are comparable across iterations of chunking/retrieval/generation.
- Local hashing embeddings understate dense quality — document that limitation next to dense-only numbers.
- Hallucination rate is reported as `1 − faithfulness` for answerable questions.
