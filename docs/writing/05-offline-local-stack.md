# Offline / local stack tradeoffs

**ContextIQ · engineering note**

ContextIQ’s portfolio default is **free and local**: sentence-transformers (BGE-small) + Ollama or extractive generation. Cloud is optional, not the bootstrap tax.

## What “free” means in numbers

| Path | API $ / query (documented) |
|------|----------------------------|
| Extractive generator | **$0** |
| Ollama local LLM | **$0** API (device power not metered) |
| Bedrock Claude 3 Haiku (optional) | list **$0.25 / $1.25** per 1M in/out tokens |

Example Haiku estimate for 312 input · 37 output tokens: **≈ $0.000124** (`docs/cost-model.md`).

Quality on the local extractive path (committed eval): context recall **89.3%**, faithfulness **100%**, refusal **100%** — enough to demo grounding without a cloud bill.

## Tradeoffs we accepted

| Choice | Win | Cost |
|--------|-----|------|
| BGE-small 384‑d | Free, strong enough for hybrid | First download ~model size; Compose image heavier |
| Extractive default in Compose | Deterministic cites, $0 | Less fluent than a good LLM |
| Ollama optional | Fluent local answers | Pull models; daemon must be up |
| Embeddings gitignored | Repo stays small | Must **bake** before Compose/host |
| Hash embedder in CI | No HF/torch on every PR | Weak dense — gate judges published JSON |

## What we did not pretend

- Extractive faithfulness ≈ 100% is not “GPT‑4 with citations.” It means answers were taken from context.
- Local $0 is not zero ops: bake embeddings, run Compose or venv, watch rate limits on a public demo ([docs/security.md](../security.md)).

## Decision

Default to local; document Bedrock as an escape hatch with real list rates. Show quality vs $ in the eval UI (`docs/eval-results/cost-tradeoffs.json`).

See: [ADR 010](../decisions/010-free-local-stack.md) · [ADR 017](../decisions/017-cost-awareness.md) · [runbook](../runbook-production.md).

## Sources

- `docs/cost-model.md`
- `docs/eval-results/cost-tradeoffs.json`
- `docs/eval-results/rag-metrics.json`
- `docs/decisions/010-free-local-stack.md`
