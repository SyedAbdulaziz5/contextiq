from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contextiq_ingestion.chunking.evaluate import BM25Index, load_golden
from contextiq_ingestion.chunking.runner import default_chunks_dir, load_chunks
from contextiq_ingestion.config import repo_root
from contextiq_ingestion.embeddings.cache import cache_path, load_embedding_cache
from contextiq_ingestion.evaluation.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
    hallucination_rate,
)
from contextiq_ingestion.generation.evaluate import is_refusal_answer
from contextiq_ingestion.generation.local import LocalGroundedGenerator
from contextiq_ingestion.generation.pipeline import build_chat_pipeline
from contextiq_ingestion.retrieval.hybrid import Mode, build_retriever
from contextiq_ingestion.retrieval.types import RankedHit


def _avg(xs: list[float]) -> float:
    return round(sum(xs) / len(xs), 4) if xs else 0.0


def _pct(x: float) -> float:
    return round(100.0 * x, 1)


def _sources_as_hits(result) -> list[RankedHit]:
    hits: list[RankedHit] = []
    for i, s in enumerate(result.answer.sources, start=1):
        hits.append(
            RankedHit(
                chunk_key=s.chunk_key,
                source_id=s.doc_source_id,
                content=s.snippet,
                score=float(s.score or 0.0),
                rank=i,
                section_title=s.section_title,
                family=s.family,
                source_url=s.source_url,
                title=s.title,
                channels=list(s.channels or []),
            )
        )
    return hits


def run_rag_suite(
    *,
    strategy: str = "structural",
    mode: Mode = "hybrid_rerank",
    top_k: int = 5,
    generator: str | None = "local",
    limit: int | None = None,
) -> dict[str, Any]:
    """
    Full Phase 7 suite on the golden set:
    context precision/recall, faithfulness, answer relevancy, refusal accuracy.
    """
    pipeline = build_chat_pipeline(strategy=strategy, generator=generator)
    path = repo_root() / "eval" / "golden.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if limit:
        rows = rows[:limit]

    precisions: list[float] = []
    recalls: list[float] = []
    faiths: list[float] = []
    relevancies: list[float] = []
    halluc_rates: list[float] = []
    refusal_correct = 0
    refusal_total = 0
    answerable = 0
    details: list[dict[str, Any]] = []

    for raw in rows:
        qid = raw["id"]
        category = raw["category"]
        question = raw["question"]
        expected = list(raw.get("expected_source_ids") or [])

        result = pipeline.ask(question, top_k=top_k, retrieval_mode=mode, force_rag=True)
        hit_list = _sources_as_hits(result)
        answer_text = result.answer.display_answer or result.answer.answer
        refused = result.answer.insufficient_context or is_refusal_answer(
            result.answer.answer, insufficient=False
        )
        contexts = [h.content for h in hit_list]

        if category == "unanswerable":
            refusal_total += 1
            ok = refused
            if ok:
                refusal_correct += 1
            f = 1.0 if refused else faithfulness(answer_text, contexts, refused=False)
            ar = answer_relevancy(question, answer_text, refused=refused)
            faiths.append(f)
            relevancies.append(ar)
            details.append(
                {
                    "id": qid,
                    "category": category,
                    "refused": refused,
                    "refusal_correct": ok,
                    "faithfulness": round(f, 4),
                    "answer_relevancy": round(ar, 4),
                }
            )
            continue

        if not expected:
            continue

        answerable += 1
        p = context_precision(hit_list, expected)
        r = context_recall(hit_list, expected)
        f = faithfulness(answer_text, contexts, refused=refused)
        ar = answer_relevancy(question, answer_text, refused=refused)
        hr = hallucination_rate(answer_text, contexts, refused=refused)
        precisions.append(p)
        recalls.append(r)
        faiths.append(f)
        relevancies.append(ar)
        halluc_rates.append(hr)
        details.append(
            {
                "id": qid,
                "category": category,
                "context_precision": round(p, 4),
                "context_recall": round(r, 4),
                "faithfulness": round(f, 4),
                "answer_relevancy": round(ar, 4),
                "hallucination_rate": round(hr, 4),
                "refused": refused,
                "retrieved": [h.source_id for h in hit_list],
            }
        )

    metrics = {
        "context_precision": _avg(precisions),
        "context_recall": _avg(recalls),
        "faithfulness": _avg(faiths),
        "answer_relevancy": _avg(relevancies),
        "refusal_accuracy": round(refusal_correct / refusal_total, 4)
        if refusal_total
        else None,
        "hallucination_rate": _avg(halluc_rates),
    }
    return {
        "suite": "rag_metrics",
        "strategy": strategy,
        "mode": mode,
        "top_k": top_k,
        "generator": generator or "local",
        "queries_evaluated": len(rows),
        "answerable_evaluated": answerable,
        "unanswerable_evaluated": refusal_total,
        "metrics": metrics,
        "metrics_pct": {k: _pct(v) if v is not None else None for k, v in metrics.items()},
        "details": details,
    }


def run_experiment_matrix(
    *,
    top_k: int = 5,
    strategies: list[str] | None = None,
) -> dict[str, Any]:
    """Compare chunking strategies (BM25) + hybrid+rerank (structural)."""
    import time

    selected = strategies or ["fixed", "structural", "semantic"]
    golden = [g for g in load_golden() if g.expected_source_ids]
    generator = LocalGroundedGenerator()
    experiments: list[dict[str, Any]] = []
    root = default_chunks_dir()

    labels = {
        "fixed": "Fixed chunks",
        "structural": "Structural chunks",
        "semantic": "Semantic chunks",
    }

    for name in selected:
        path = root / name / "chunks.jsonl"
        if not path.exists():
            experiments.append(
                {
                    "name": labels.get(name, name),
                    "strategy": name,
                    "backend": "sparse_bm25",
                    "top_k": top_k,
                    "error": f"missing {path}",
                }
            )
            continue
        chunks = load_chunks(path)
        index = BM25Index(chunks)
        recalls: list[float] = []
        faiths: list[float] = []
        latencies: list[float] = []
        for item in golden:
            t0 = time.perf_counter()
            pairs = index.search(item.question, k=top_k)
            hits: list[RankedHit] = []
            for i, (chunk, score) in enumerate(pairs, start=1):
                hits.append(
                    RankedHit(
                        chunk_key=chunk.chunk_id,
                        source_id=chunk.source_id,
                        content=chunk.content,
                        score=float(score),
                        rank=i,
                        section_title=chunk.section_title,
                        family=chunk.family,
                        source_url=chunk.source_url,
                        title=chunk.title,
                        channels=["sparse"],
                    )
                )
            grounded = generator.generate(item.question, hits)
            latencies.append((time.perf_counter() - t0) * 1000)
            recalls.append(context_recall(hits, item.expected_source_ids))
            answer = grounded.display_answer or grounded.answer
            faiths.append(
                faithfulness(
                    answer,
                    [h.content for h in hits],
                    refused=grounded.insufficient_context,
                )
            )

        experiments.append(
            {
                "name": labels.get(name, f"{name} chunks"),
                "strategy": name,
                "backend": "sparse_bm25",
                "top_k": top_k,
                "retriever": "Sparse BM25 only",
                "reranker": "None",
                "recall": _avg(recalls),
                "faithfulness": _avg(faiths),
                "recall_pct": _pct(_avg(recalls)),
                "faithfulness_pct": _pct(_avg(faiths)),
                "latency_ms_avg": round(_avg(latencies), 1) if latencies else None,
                "n": len(golden),
            }
        )

    cache = cache_path("structural")
    if cache.exists():
        rows = load_embedding_cache(cache)
        retriever = build_retriever(rows, provider="local")
        recalls = []
        faiths = []
        latencies = []
        for item in golden:
            t0 = time.perf_counter()
            hits = retriever.retrieve(item.question, mode="hybrid_rerank", top_k=top_k)
            grounded = generator.generate(item.question, hits)
            latencies.append((time.perf_counter() - t0) * 1000)
            recalls.append(context_recall(hits, item.expected_source_ids))
            answer = grounded.display_answer or grounded.answer
            faiths.append(
                faithfulness(
                    answer,
                    [h.content for h in hits],
                    refused=grounded.insufficient_context,
                )
            )
        experiments.append(
            {
                "name": "Hybrid + reranker",
                "strategy": "structural",
                "backend": "hybrid_rerank",
                "top_k": top_k,
                "retriever": "Dense + sparse (BM25) → RRF",
                "reranker": "Feature / lexical reranker",
                "recall": _avg(recalls),
                "faithfulness": _avg(faiths),
                "recall_pct": _pct(_avg(recalls)),
                "faithfulness_pct": _pct(_avg(faiths)),
                "latency_ms_avg": round(_avg(latencies), 1) if latencies else None,
                "n": len(golden),
            }
        )

    # Deltas vs production default (hybrid + reranker) when present
    prod = next((e for e in experiments if e.get("name") == "Hybrid + reranker"), None)
    if prod and prod.get("recall_pct") is not None:
        for e in experiments:
            if e.get("recall_pct") is None:
                continue
            e["delta_recall_pp"] = round(
                (float(e["recall_pct"]) - float(prod["recall_pct"])) * 10
            ) / 10
            if e.get("latency_ms_avg") is not None and prod.get("latency_ms_avg") is not None:
                e["delta_latency_ms"] = round(
                    float(e["latency_ms_avg"]) - float(prod["latency_ms_avg"]), 1
                )

    ranking = sorted(
        [e for e in experiments if "recall" in e],
        key=lambda e: (e["recall"], e["faithfulness"]),
        reverse=True,
    )
    production_rationale = (
        "Production default is structural chunking + hybrid_rerank: "
        "hybrid closes keyword misses that pure dense search leaves, "
        "reranking improves citation precision, and structural chunks "
        "preserve section boundaries better than semantic splits on this corpus. "
        "Fixed-size chunks can win raw BM25 recall in isolation but lose "
        "structure and hybrid quality in the full pipeline."
    )
    return {
        "suite": "experiments",
        "top_k": top_k,
        "notes": (
            "Faithfulness is near-ceiling with the local extractive generator "
            "(answers are copied from context). Recall differentiates setups. "
            "Production default remains structural + hybrid_rerank."
        ),
        "production_rationale": production_rationale,
        "experiments": experiments,
        "winner": ranking[0]["name"] if ranking else None,
        "production_default": "Hybrid + reranker",
        "table": [
            {
                "experiment": e["name"],
                "recall": e.get("recall_pct"),
                "faithfulness": e.get("faithfulness_pct"),
                "latency_ms_avg": e.get("latency_ms_avg"),
                "delta_recall_pp": e.get("delta_recall_pp"),
            }
            for e in experiments
            if "recall_pct" in e
        ],
    }


def publish_results(
    suite: dict[str, Any],
    experiments: dict[str, Any],
) -> dict[str, Path]:
    root = repo_root()
    docs = root / "docs" / "eval-results"
    docs.mkdir(parents=True, exist_ok=True)
    public = root / "apps" / "web" / "public" / "eval"
    public.mkdir(parents=True, exist_ok=True)

    # Slim suite for dashboard (drop per-question details)
    slim_suite = {k: v for k, v in suite.items() if k != "details"}
    from contextiq_ingestion.evaluation.workspace import (
        build_comparison,
        enrich_experiment,
    )

    baseline_path = repo_root() / "eval" / "ci" / "baseline.json"
    baseline = {}
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    current_pct = suite.get("metrics_pct") or {}
    baseline_pct = baseline.get("metrics_pct") or {}
    top_k = int(experiments.get("top_k") or 5)
    prod_name = experiments.get("production_default")
    prod_recall = None
    for e in experiments.get("experiments") or []:
        if e.get("name") == prod_name:
            prod_recall = e.get("recall_pct")
            break
    details = [
        enrich_experiment(e, top_k=top_k, baseline_recall=prod_recall)
        for e in (experiments.get("experiments") or [])
    ]
    dashboard = {
        "title": "Evaluation workspace",
        "queries_evaluated": suite.get("queries_evaluated"),
        "metrics_pct": suite.get("metrics_pct"),
        "metrics": suite.get("metrics"),
        "strategy": suite.get("strategy"),
        "mode": suite.get("mode"),
        "generator": suite.get("generator"),
        "experiments": experiments.get("table"),
        "experiment_details": details,
        "winner": experiments.get("winner"),
        "production_default": experiments.get("production_default"),
        "production_rationale": experiments.get("production_rationale"),
        "notes": experiments.get("notes"),
        "top_k": top_k,
        "baseline": {
            "ref": baseline.get("ref") or "baseline",
            "metrics_pct": baseline_pct,
            "strategy": baseline.get("strategy"),
            "mode": baseline.get("mode"),
        },
        "comparison": build_comparison(current_pct, baseline_pct),
        "workspace_version": 11,
    }

    paths = {
        "suite": docs / "rag-metrics.json",
        "experiments": docs / "experiments.json",
        "dashboard": docs / "dashboard.json",
        "public": public / "latest.json",
        "markdown": root / "docs" / "eval-results.md",
    }
    paths["suite"].write_text(json.dumps({**slim_suite, "details": suite.get("details")}, indent=2) + "\n")
    paths["experiments"].write_text(json.dumps(experiments, indent=2) + "\n")
    paths["dashboard"].write_text(json.dumps(dashboard, indent=2) + "\n")
    paths["public"].write_text(json.dumps(dashboard, indent=2) + "\n")
    paths["markdown"].write_text(_markdown_report(suite, experiments))
    return paths


def _markdown_report(suite: dict[str, Any], experiments: dict[str, Any]) -> str:
    m = suite.get("metrics_pct") or {}
    lines = [
        "# ContextIQ RAG Evaluation",
        "",
        f"Queries evaluated: **{suite.get('queries_evaluated')}**  ",
        f"Pipeline: `{suite.get('strategy')}` + `{suite.get('mode')}` + `{suite.get('generator')}`",
        "",
        "## Headline metrics",
        "",
        "| Metric | Score |",
        "|---|---|",
        f"| Context Precision | {m.get('context_precision')}% |",
        f"| Context Recall | {m.get('context_recall')}% |",
        f"| Faithfulness | {m.get('faithfulness')}% |",
        f"| Answer Relevancy | {m.get('answer_relevancy')}% |",
        f"| Refusal Accuracy | {m.get('refusal_accuracy')}% |",
        "",
        "## Experiments (Recall × Faithfulness)",
        "",
        "| Experiment | Recall | Faithfulness |",
        "|---|---|---|",
    ]
    for row in experiments.get("table") or []:
        lines.append(
            f"| {row['experiment']} | {row['recall']}% | {row['faithfulness']}% |"
        )
    lines.extend(
        [
            "",
            f"**Best recall (this run):** {experiments.get('winner')}  ",
            f"**Production default:** {experiments.get('production_default')}",
            "",
            experiments.get("notes") or "",
            "",
            "Raw JSON: [`rag-metrics.json`](eval-results/rag-metrics.json), "
            "[`experiments.json`](eval-results/experiments.json).",
            "",
            "Regenerate:",
            "",
            "```bash",
            "contextiq-eval run",
            "```",
            "",
        ]
    )
    return "\n".join(lines) + "\n"
