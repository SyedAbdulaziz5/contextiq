"""Assemble evaluation workspace payload: current vs baseline + experiment detail."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contextiq_ingestion.config import repo_root

COMPARE_KEYS = [
    ("context_recall", "Retrieval Recall"),
    ("context_precision", "Context Precision"),
    ("faithfulness", "Faithfulness"),
    ("answer_relevancy", "Answer Relevancy"),
    ("refusal_accuracy", "Refusal Accuracy"),
]


def _pct(v: float | None) -> float | None:
    if v is None:
        return None
    return round(float(v) * 1000) / 10


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics_pct(blob: dict[str, Any]) -> dict[str, float | None]:
    if blob.get("metrics_pct"):
        return {k: blob["metrics_pct"].get(k) for k, _ in COMPARE_KEYS}
    raw = blob.get("metrics") or {}
    return {k: _pct(raw.get(k)) if raw.get(k) is not None else None for k, _ in COMPARE_KEYS}


def build_comparison(
    current_pct: dict[str, float | None],
    baseline_pct: dict[str, float | None],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, label in COMPARE_KEYS:
        cur = current_pct.get(key)
        base = baseline_pct.get(key)
        delta = None
        if cur is not None and base is not None:
            delta = round((cur - base) * 10) / 10
        rows.append(
            {
                "key": key,
                "label": label,
                "current": cur,
                "baseline": base,
                "delta_pp": delta,
            }
        )
    return rows


def enrich_experiment(
    exp: dict[str, Any], *, top_k: int, baseline_recall: float | None
) -> dict[str, Any]:
    """Attach retriever config + recall delta vs production hybrid default."""
    backend = str(exp.get("backend") or "")
    strategy = str(exp.get("strategy") or "")
    name = str(exp.get("name") or exp.get("experiment") or "experiment")

    if backend == "hybrid_rerank":
        retriever = "Dense + sparse (BM25) → RRF"
        reranker = "Feature / lexical reranker"
        mode = "hybrid_rerank"
    elif backend == "sparse_bm25":
        retriever = "Sparse BM25 only"
        reranker = "None"
        mode = "sparse"
    else:
        retriever = backend or "unknown"
        reranker = "—"
        mode = backend or "—"

    recall = exp.get("recall_pct")
    if recall is None and exp.get("recall") is not None:
        r = exp["recall"]
        recall = r if r > 1 else _pct(float(r))
    faith = exp.get("faithfulness_pct")
    if faith is None and exp.get("faithfulness") is not None:
        f = exp["faithfulness"]
        faith = f if f > 1 else _pct(float(f))

    delta_recall = None
    if recall is not None and baseline_recall is not None:
        delta_recall = round((float(recall) - float(baseline_recall)) * 10) / 10

    return {
        "name": name,
        "experiment": name,
        "strategy": strategy,
        "backend": backend,
        "retriever": retriever,
        "reranker": reranker,
        "mode": mode,
        "top_k": exp.get("top_k", top_k),
        "chunking": strategy or "—",
        "recall": recall,
        "faithfulness": faith,
        "latency_ms_avg": exp.get("latency_ms_avg"),
        "delta_recall_pp": delta_recall,
        "delta_latency_ms": exp.get("delta_latency_ms"),
        "n": exp.get("n"),
        "error": exp.get("error"),
    }


def assemble_workspace(*, root: Path | None = None) -> dict[str, Any]:
    """Build the Phase 11 evaluation workspace payload from on-disk artifacts."""
    root = root or repo_root()
    dash_path = root / "docs" / "eval-results" / "dashboard.json"
    suite_path = root / "docs" / "eval-results" / "rag-metrics.json"
    exp_path = root / "docs" / "eval-results" / "experiments.json"
    baseline_path = root / "eval" / "ci" / "baseline.json"

    dashboard = _load(dash_path)
    suite = _load(suite_path)
    experiments_blob = _load(exp_path)
    baseline = _load(baseline_path)

    if dashboard.get("metrics_pct") or dashboard.get("metrics"):
        current_pct = _metrics_pct(dashboard)
    else:
        current_pct = _metrics_pct(suite)
    if not any(v is not None for v in current_pct.values()):
        current_pct = _metrics_pct(suite)
    baseline_pct = _metrics_pct(baseline)

    top_k = int(experiments_blob.get("top_k") or 5)
    raw_exps = list(experiments_blob.get("experiments") or [])
    if not raw_exps:
        raw_exps = [
            {
                "name": r.get("experiment"),
                "recall_pct": r.get("recall"),
                "faithfulness_pct": r.get("faithfulness"),
            }
            for r in (dashboard.get("experiments") or experiments_blob.get("table") or [])
        ]

    prod_name = experiments_blob.get("production_default") or dashboard.get(
        "production_default"
    )
    prod_recall = None
    for e in raw_exps:
        label = e.get("name") or e.get("experiment")
        if label == prod_name:
            prod_recall = e.get("recall_pct")
            if prod_recall is None and e.get("recall") is not None:
                r = e["recall"]
                prod_recall = r if r > 1 else _pct(float(r))
            break

    details = [
        enrich_experiment(e, top_k=top_k, baseline_recall=prod_recall) for e in raw_exps
    ]

    production_rationale = (
        experiments_blob.get("production_rationale")
        or dashboard.get("production_rationale")
        or (
            "Production default is structural chunking + hybrid_rerank: "
            "hybrid closes keyword misses that pure dense search leaves, "
            "reranking improves citation precision, and structural chunks "
            "preserve section boundaries better than semantic splits on this corpus. "
            "Fixed-size chunks can win raw BM25 recall in isolation but lose "
            "structure and hybrid quality in the full pipeline."
        )
    )

    out: dict[str, Any] = {
        **dashboard,
        "title": dashboard.get("title") or "Evaluation workspace",
        "metrics_pct": current_pct
        if any(v is not None for v in current_pct.values())
        else dashboard.get("metrics_pct"),
        "baseline": {
            "ref": baseline.get("ref") or "baseline",
            "metrics_pct": baseline_pct,
            "strategy": baseline.get("strategy"),
            "mode": baseline.get("mode"),
            "generator": baseline.get("generator"),
            "queries_evaluated": baseline.get("queries_evaluated"),
            "notes": baseline.get("notes"),
        },
        "comparison": build_comparison(current_pct, baseline_pct),
        "experiment_details": details,
        "experiments": dashboard.get("experiments")
        or experiments_blob.get("table")
        or [
            {
                "experiment": d["name"],
                "recall": d["recall"],
                "faithfulness": d["faithfulness"],
            }
            for d in details
            if d.get("recall") is not None
        ],
        "winner": experiments_blob.get("winner") or dashboard.get("winner"),
        "production_default": prod_name,
        "production_rationale": production_rationale,
        "notes": experiments_blob.get("notes") or dashboard.get("notes"),
        "top_k": top_k,
        "workspace_version": 11,
    }

    if suite.get("details") and "failed_queries" not in out:
        failed = [
            d
            for d in suite["details"]
            if (
                d.get("refusal_correct") is False
                or (
                    d.get("category") != "unanswerable"
                    and (
                        (d.get("context_recall") or 1) < 0.5
                        or (d.get("faithfulness") or 1) < 0.8
                        or d.get("refused")
                    )
                )
            )
        ]
        out["failed_queries"] = failed[:40]
        out["failed_count"] = len(failed)

    return out
