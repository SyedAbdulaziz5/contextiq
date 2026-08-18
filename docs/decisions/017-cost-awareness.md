# ADR 017 — Cost awareness (documented pricing)

## Status

Accepted

## Context

Portfolio demos often show `$0.00000` without explaining why, or invent cloud costs. Recruiters should see **quality vs $ vs latency** with sourced assumptions.

## Decision

1. Single pricing table in `observability/cost.py` + `docs/cost-model.md`.
2. Free paths (extractive, Ollama) are **$0 API**; Bedrock Haiku uses list rates **$0.25 / $1.25 per 1M** tokens.
3. Every trace stores `cost_usd` and a `cost` detail object (label, note, rates).
4. Eval workspace shows **Quality · latency · cost** comparisons from `docs/eval-results/cost-tradeoffs.json` (metrics from real eval artifacts; Bedrock $ computed from the documented formula).
5. Token counts remain a word-split proxy — documented as approximate.

## Consequences

- Request breakdown explains $0 vs paid paths.
- Switching models means updating the pricing table + cost-model doc together.

## References

- `docs/cost-model.md`
