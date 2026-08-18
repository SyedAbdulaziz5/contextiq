from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contextiq_ingestion.chunking.evaluate import load_golden, source_recall_at_k
from contextiq_ingestion.config import repo_root
from contextiq_ingestion.embeddings.cache import cache_path, load_embedding_cache
from contextiq_ingestion.query.pipeline import build_query_pipeline
from contextiq_ingestion.query.rewriter import Turn
from contextiq_ingestion.query.router import QueryRouter, Route


ROUTER_FIXTURES: list[dict[str, Any]] = [
    {"query": "Hi", "expect": Route.GREETING.value},
    {"query": "hello!", "expect": Route.GREETING.value},
    {"query": "What can you do?", "expect": Route.META.value},
    {"query": "what is 12 + 30?", "expect": Route.CALCULATION.value},
    {"query": "what about the second one?", "expect": Route.CLARIFY.value},
    {"query": "What is the Lambda timeout?", "expect": Route.RAG.value},
    {"query": "amazon.titan-embed-text-v2:0 dimensions", "expect": Route.RAG.value},
]

REWRITE_FIXTURES: list[dict[str, Any]] = [
    {
        "history": [
            {"role": "user", "content": "Tell me about Next.js Server Components"},
        ],
        "query": "what about the second one?",
        "must_contain_any": ["server component", "Server Component", "limitations"],
    },
    {
        "history": [
            {"role": "user", "content": "What is the maximum Lambda timeout?"},
        ],
        "query": "tell me more about that",
        "must_contain_any": ["timeout", "Lambda", "maximum"],
    },
    {
        "history": [],
        "query": "What is amazon.titan-embed-text-v2:0?",
        "must_contain_any": ["amazon.titan-embed-text-v2:0"],
        "changed": False,
    },
]


def eval_router() -> dict[str, Any]:
    router = QueryRouter()
    rows = []
    correct = 0
    for fix in ROUTER_FIXTURES:
        decision = router.route(fix["query"], has_history=False)
        ok = decision.route.value == fix["expect"]
        correct += int(ok)
        rows.append(
            {
                "query": fix["query"],
                "expect": fix["expect"],
                "got": decision.route.value,
                "ok": ok,
                "reason": decision.reason,
                "reply": decision.reply,
            }
        )
    return {
        "accuracy": round(correct / len(ROUTER_FIXTURES), 4),
        "n": len(ROUTER_FIXTURES),
        "cases": rows,
    }


def eval_rewriter() -> dict[str, Any]:
    from contextiq_ingestion.query.rewriter import QueryRewriter

    rewriter = QueryRewriter()
    rows = []
    correct = 0
    for fix in REWRITE_FIXTURES:
        history = [Turn(**t) for t in fix["history"]]
        result = rewriter.rewrite(fix["query"], history)
        needles = fix.get("must_contain_any") or []
        contains = any(n.lower() in result.rewritten.lower() for n in needles)
        changed_ok = True
        if "changed" in fix:
            changed_ok = result.changed is fix["changed"]
        ok = contains and changed_ok
        correct += int(ok)
        rows.append(
            {
                "query": fix["query"],
                "rewritten": result.rewritten,
                "changed": result.changed,
                "ok": ok,
                "reason": result.reason,
            }
        )
    return {
        "accuracy": round(correct / len(REWRITE_FIXTURES), 4),
        "n": len(REWRITE_FIXTURES),
        "cases": rows,
    }


def eval_hyde_ab(
    *,
    strategy: str = "structural",
    provider: str | None = None,
    hyde_provider: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    A/B test: dense channel fed by raw rewritten query vs HyDE document.
    Sparse channel always uses the rewritten query.
    Retrieval mode: hybrid_rerank.
    """
    rows = load_embedding_cache(cache_path(strategy))
    pipeline = build_query_pipeline(rows, provider=provider, hyde_provider=hyde_provider)
    golden = [g for g in load_golden() if g.expected_source_ids]

    def run(dense_strategy: str) -> dict[str, float]:
        recalls: list[float] = []
        for item in golden:
            result = pipeline.run(
                item.question,
                dense_strategy=dense_strategy,  # type: ignore[arg-type]
                retrieval_mode="hybrid_rerank",
                top_k=top_k,
                force_rag=True,
            )
            recalls.append(source_recall_at_k(result.hits, item.expected_source_ids))  # type: ignore[arg-type]
        return {
            f"recall@{top_k}": round(sum(recalls) / len(recalls), 4) if recalls else 0.0
        }

    raw = run("raw")
    hyde = run("hyde")
    delta = round(hyde[f"recall@{top_k}"] - raw[f"recall@{top_k}"], 4)
    verdict = (
        "hyde_better"
        if delta > 0.01
        else "raw_better"
        if delta < -0.01
        else "tie"
    )
    return {
        "strategy": strategy,
        "top_k": top_k,
        "n": len(golden),
        "raw": raw,
        "hyde": hyde,
        "delta_hyde_minus_raw": delta,
        "verdict": verdict,
        "note": (
            "Template HyDE is an offline stand-in. Re-run with CONTEXTIQ_HYDE_PROVIDER=bedrock "
            "before concluding HyDE helps in production."
        ),
    }


def run_all_query_evals(
    *,
    strategy: str = "structural",
    provider: str | None = None,
    hyde_provider: str | None = None,
) -> dict[str, Any]:
    out = {
        "router": eval_router(),
        "rewriter": eval_rewriter(),
        "hyde_ab": eval_hyde_ab(
            strategy=strategy, provider=provider, hyde_provider=hyde_provider
        ),
    }
    path = repo_root() / "docs" / "eval-results" / "query-understanding.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out
