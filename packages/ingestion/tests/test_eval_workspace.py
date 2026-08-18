from __future__ import annotations

from contextiq_ingestion.evaluation.workspace import (
    assemble_workspace,
    build_comparison,
    enrich_experiment,
)


def test_build_comparison_deltas():
    rows = build_comparison(
        {"context_recall": 89.3, "faithfulness": 100.0, "answer_relevancy": 68.7,
         "context_precision": 41.6, "refusal_accuracy": 100.0},
        {"context_recall": 89.3, "faithfulness": 100.0, "answer_relevancy": 68.7,
         "context_precision": 41.6, "refusal_accuracy": 100.0},
    )
    assert len(rows) == 5
    assert all(r["delta_pp"] == 0.0 for r in rows)


def test_build_comparison_regression():
    rows = build_comparison(
        {"context_recall": 87.0, "faithfulness": 100.0, "answer_relevancy": None,
         "context_precision": None, "refusal_accuracy": 100.0},
        {"context_recall": 89.3, "faithfulness": 100.0, "answer_relevancy": 68.7,
         "context_precision": 41.6, "refusal_accuracy": 100.0},
    )
    recall = next(r for r in rows if r["key"] == "context_recall")
    assert recall["delta_pp"] == -2.3


def test_enrich_experiment_vs_hybrid():
    detail = enrich_experiment(
        {
            "name": "Fixed chunks",
            "strategy": "fixed",
            "backend": "sparse_bm25",
            "recall_pct": 91.1,
            "faithfulness_pct": 100.0,
        },
        top_k=5,
        baseline_recall=89.3,
    )
    assert detail["retriever"].startswith("Sparse")
    assert detail["reranker"] == "None"
    assert detail["top_k"] == 5
    assert detail["delta_recall_pp"] == 1.8


def test_assemble_workspace_from_repo():
    ws = assemble_workspace()
    assert ws.get("comparison")
    assert ws.get("experiment_details")
    assert ws.get("production_default") == "Hybrid + reranker"
    assert ws.get("production_rationale")
    hybrid = next(d for d in ws["experiment_details"] if d["name"] == "Hybrid + reranker")
    assert hybrid["delta_recall_pp"] == 0.0
    assert "RRF" in (hybrid.get("retriever") or "")
