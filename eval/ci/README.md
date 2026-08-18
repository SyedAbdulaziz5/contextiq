# CI evaluation gate (`eval/ci/`)

This is what blocks merges when RAG quality regresses — not vibes, numbers.

## Files

| File | Role |
|---|---|
| `baseline.json` | Metrics on `main` (promote after a green eval) |
| `thresholds.json` | Absolute floors + max allowed drop vs baseline |
| `gate-report.md` | Written by CI (gitignored) |
| `gate-result.json` | Machine-readable gate result (gitignored) |

## Flow

```text
GitHub PR
  → Lint / Typecheck / Tests
  → contextiq-eval gate
  → Compare PR metrics vs baseline
  → Comment on PR
  → PASS / FAIL (merge blocked on FAIL)
```

## Local

```bash
# After changing retrieval/generation, re-measure and commit:
contextiq-eval run
contextiq-eval gate

# After merging a deliberate quality change to main:
contextiq-eval promote-baseline
git add eval/ci/baseline.json && git commit -m "chore: promote RAG eval baseline"
```

## Thresholds (current)

Absolute floors (examples):

- Context Recall ≥ 85%
- Faithfulness ≥ 90%
- Refusal Accuracy ≥ 90%

Plus max regression vs `baseline.json` (e.g. Faithfulness may not drop more than 2 pts).
