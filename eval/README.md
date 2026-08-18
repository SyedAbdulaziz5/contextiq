# Evaluation set (`eval/`)

This folder is the quality bar for ContextIQ. Nothing in retrieval or generation is "done" until it improves (or at least does not regress) these labels.

## Files

| File | Role |
|---|---|
| `golden.jsonl` | One JSON object per line — hand-labeled Q/A with source IDs |
| `README.md` | This file |
| `schema.json` | JSON Schema for each golden record |
| `validate_golden.py` | Local validator (run before committing eval changes) |

## Record schema

```json
{
  "id": "q001",
  "question": "What is the maximum execution timeout for an AWS Lambda function?",
  "expected_answer": "900 seconds (15 minutes).",
  "expected_source_ids": ["aws-lambda-limits"],
  "category": "factual",
  "difficulty": "easy",
  "notes": "Hard quota; not increasable."
}
```

### Fields

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable id `qNNN` |
| `question` | yes | Exact user question we will ask the system |
| `expected_answer` | yes | Short reference answer (not the only acceptable phrasing) |
| `expected_source_ids` | yes | Must exist in `corpus/sources.json`. Empty `[]` only for `unanswerable` |
| `category` | yes | See below |
| `difficulty` | no | `easy` \| `medium` \| `hard` |
| `notes` | no | Why this item exists / grading hints |

### Categories

| Category | Intent |
|---|---|
| `factual` | Direct fact lookup |
| `keyword` | Exact model IDs, codes, API names — hybrid/sparse should help |
| `multi_hop` | Needs ≥2 distinct sources |
| `unanswerable` | Not in corpus → must refuse |
| `ambiguous` | Underspecified → clarify or state ambiguity |
| `table` | Numbers that live in quota/limit tables |
| `edge_case` | Units, synonyms, partial phrases, tricky wording |

## How we score (Phases 7–9)

- **Context Recall / Precision, Faithfulness, Relevancy, Refusal** — see `docs/eval-results.md`
- **CI gate** — `contextiq-eval gate` compares PR metrics to `eval/ci/baseline.json` and fails the build on regression (`.github/workflows/eval.yml`)

## Commands

```bash
python eval/validate_golden.py
contextiq-eval run
contextiq-eval gate
```

Must exit 0 before merging changes that affect retrieval quality.
## Discipline

- Do **not** invent source IDs — add them to `corpus/sources.json` first.
- Prefer short `expected_answer` strings; graders care about facts + sources more than prose.
- When AWS docs change a quota, update the golden row and note it in `notes`.
