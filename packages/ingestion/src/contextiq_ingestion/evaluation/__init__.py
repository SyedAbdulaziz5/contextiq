"""Phase 7 — RAG evaluation (metrics + experiments + evidence publish)."""

from contextiq_ingestion.evaluation.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)
from contextiq_ingestion.evaluation.suite import (
    publish_results,
    run_experiment_matrix,
    run_rag_suite,
)

__all__ = [
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "faithfulness",
    "publish_results",
    "run_experiment_matrix",
    "run_rag_suite",
]
