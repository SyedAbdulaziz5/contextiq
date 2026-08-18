# ContextIQ RAG Evaluation

Queries evaluated: **75**  
Pipeline: `structural` + `hybrid_rerank` + `local`

## Headline metrics

| Metric | Score |
|---|---|
| Context Precision | 41.6% |
| Context Recall | 89.3% |
| Faithfulness | 100.0% |
| Answer Relevancy | 68.7% |
| Refusal Accuracy | 100.0% |

## Experiments (Recall × Faithfulness)

| Experiment | Recall | Faithfulness |
|---|---|---|
| Fixed chunks | 91.1% | 100.0% |
| Structural chunks | 90.9% | 100.0% |
| Semantic chunks | 80.2% | 100.0% |
| Hybrid + reranker | 89.3% | 100.0% |

**Best recall (this run):** Fixed chunks  
**Production default:** Hybrid + reranker

Faithfulness is near-ceiling with the local extractive generator (answers are copied from context). Recall differentiates setups. Production default remains structural + hybrid_rerank.

Raw JSON: [`rag-metrics.json`](eval-results/rag-metrics.json), [`experiments.json`](eval-results/experiments.json).

Regenerate:

```bash
contextiq-eval run
```

