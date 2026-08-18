from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from contextiq_ingestion.chunking.evaluate import load_golden, source_recall_at_k
from contextiq_ingestion.config import repo_root
from contextiq_ingestion.embeddings.cache import cache_path, load_embedding_cache
from contextiq_ingestion.retrieval.hybrid import Mode, build_retriever
from contextiq_ingestion.retrieval.types import RankedHit


def context_precision_at_k(hits: list[RankedHit], expected_source_ids: list[str]) -> float:
    """Fraction of retrieved chunks whose source_id is in the expected set."""
    if not hits:
        return 0.0
    expected = set(expected_source_ids)
    return sum(1 for h in hits if h.source_id in expected) / len(hits)


def evaluate_modes(
    *,
    strategy: str = "structural",
    provider: str | None = None,
    ks: tuple[int, ...] = (5, 8),
    modes: list[Mode] | None = None,
) -> dict[str, Any]:
    path = cache_path(strategy)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run: contextiq-embed upsert --strategy {strategy} --skip-postgres"
        )
    rows = load_embedding_cache(path)
    retriever = build_retriever(rows, provider=provider)
    golden = [g for g in load_golden() if g.expected_source_ids]
    selected_modes: list[Mode] = modes or ["dense", "sparse", "hybrid", "hybrid_rerank"]

    results: dict[str, Any] = {
        "strategy": strategy,
        "embedding_model": retriever.embedder.name,
        "answerable_questions": len(golden),
        "modes": {},
    }

    for mode in selected_modes:
        per_k_recall: dict[str, list[float]] = {f"recall@{k}": [] for k in ks}
        per_k_precision: dict[str, list[float]] = {f"precision@{k}": [] for k in ks}
        by_category: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        max_k = max(ks)

        for item in golden:
            hits = retriever.retrieve(item.question, mode=mode, top_k=max_k)
            # adapt RankedHit → objects with source_id for shared helper
            for k in ks:
                top = hits[:k]
                recall = source_recall_at_k(top, item.expected_source_ids)  # type: ignore[arg-type]
                precision = context_precision_at_k(top, item.expected_source_ids)
                per_k_recall[f"recall@{k}"].append(recall)
                per_k_precision[f"precision@{k}"].append(precision)
                by_category[item.category][f"recall@{k}"].append(recall)

        def avg(xs: list[float]) -> float:
            return round(sum(xs) / len(xs), 4) if xs else 0.0

        results["modes"][mode] = {
            "metrics": {
                **{k: avg(v) for k, v in per_k_recall.items()},
                **{k: avg(v) for k, v in per_k_precision.items()},
            },
            "by_category": {
                cat: {m: avg(vals) for m, vals in metrics.items()}
                for cat, metrics in sorted(by_category.items())
            },
        }

    # rank modes by recall@5 (or first k)
    primary = f"recall@{ks[0]}"
    ranking = sorted(
        (
            {
                "mode": mode,
                "recall": data["metrics"].get(primary, 0.0),
                "precision": data["metrics"].get(f"precision@{ks[0]}", 0.0),
            }
            for mode, data in results["modes"].items()
        ),
        key=lambda r: (r["recall"], r["precision"]),
        reverse=True,
    )
    results["winner"] = ranking[0]["mode"] if ranking else None
    results["ranking"] = ranking

    out = repo_root() / "docs" / "eval-results" / "hybrid-retrieval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return results


# Recruiter-facing demo queries (illustrate why each channel exists)
DEMO_QUERIES: list[dict[str, str]] = [
    {
        "id": "paraphrase",
        "question": "What's the longest a Lambda function is allowed to run?",
        "why": "Paraphrase of timeout — dense helps when embeddings are strong; sparse still catches 'Lambda'/'run'.",
        "expect_source": "aws-lambda-limits",
    },
    {
        "id": "exact_id",
        "question": "What is amazon.titan-embed-text-v2:0?",
        "why": "Exact model ID — keyword/sparse should dominate pure vector search.",
        "expect_source": "aws-bedrock-titan-embeddings",
    },
    {
        "id": "error_code",
        "question": "What HTTP status code does Lambda return when throttled?",
        "why": "Exact code 429 — sparse/hybrid recovers identifiers dense often misses.",
        "expect_source": "aws-lambda-scaling",
    },
    {
        "id": "next_api",
        "question": "How do I use useSearchParams in the Next.js App Router?",
        "why": "API-name lookup in Next.js docs — sparse/hybrid for exact symbol.",
        "expect_source": "nextjs-linking-and-navigating",
    },
]


def run_demos(
    *,
    strategy: str = "structural",
    provider: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    rows = load_embedding_cache(cache_path(strategy))
    retriever = build_retriever(rows, provider=provider)
    report: list[dict[str, Any]] = []
    for demo in DEMO_QUERIES:
        q = demo["question"]
        row: dict[str, Any] = {
            "id": demo["id"],
            "question": q,
            "why": demo["why"],
            "expect_source": demo["expect_source"],
            "modes": {},
        }
        for mode in ("dense", "sparse", "hybrid", "hybrid_rerank"):
            hits = retriever.retrieve(q, mode=mode, top_k=top_k)  # type: ignore[arg-type]
            sources = [h.source_id for h in hits]
            row["modes"][mode] = {
                "top_sources": sources,
                "hit_expected": demo["expect_source"] in sources,
                "top1": sources[0] if sources else None,
                "channels_top1": hits[0].channels if hits else [],
            }
        report.append(row)
    return report
