# ContextIQ cost model

How we estimate per-request cost. **No invented prices** — free paths are $0; cloud uses published list rates.

## Generators

| Key | Label | Billing | Input USD/1M | Output USD/1M |
|---|---|---|---:|---:|
| `extractive` | Local extractive | none | 0 | 0 |
| `ollama` | Ollama (local) | none | 0 | 0 |
| `bedrock_haiku` | Bedrock Claude 3 Haiku | per token | **0.25** | **1.25** |

Bedrock rates: AWS Bedrock on-demand list price for Claude 3 Haiku (USD per million tokens). Update `observability/cost.py` if the project switches models.

## Token estimate

ContextIQ uses a **word-count proxy** (`max(1, len(text.split()))`), not a provider tokenizer. Good enough for order-of-magnitude demos; not for finance reconciliation.

## Formula (paid)

```text
cost_usd = (input_tokens * input_usd_per_m + output_tokens * output_usd_per_m) / 1_000_000
```

Example (312 in · 37 out on Haiku):

```text
(312 * 0.25 + 37 * 1.25) / 1e6 ≈ $0.000124
```

## What we do **not** meter

- Electricity / GPU for Ollama or sentence-transformers  
- Developer time  
- Postgres / hosting (Phase 18)

## Where it shows up

- Every trace: `cost_usd` + `cost` detail (`label`, `note`, rates)  
- Chat / Traces: Request breakdown  
- Eval: Quality · latency · cost tradeoffs (`docs/eval-results/cost-tradeoffs.json`)

## Commands

```python
from contextiq_ingestion.observability.cost import estimate_cost_detail, pricing_catalog
print(estimate_cost_detail(input_tokens=312, output_tokens=37, generator="bedrock"))
print(pricing_catalog())
```
