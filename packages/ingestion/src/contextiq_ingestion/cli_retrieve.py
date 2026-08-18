from __future__ import annotations

import argparse
import json
import logging
import sys

from contextiq_ingestion.embeddings.cache import cache_path, load_embedding_cache
from contextiq_ingestion.retrieval.evaluate import evaluate_modes, run_demos
from contextiq_ingestion.retrieval.hybrid import build_retriever


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextiq-retrieve",
        description="ContextIQ Phase 4 — hybrid retrieval (dense + sparse → RRF → rerank)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Retrieve with dense|sparse|hybrid|hybrid_rerank")
    search.add_argument("query")
    search.add_argument(
        "--mode",
        default="hybrid_rerank",
        choices=["dense", "sparse", "hybrid", "hybrid_rerank"],
    )
    search.add_argument("--strategy", default="structural")
    search.add_argument("--top-k", type=int, default=8)
    search.add_argument("--family", default=None)
    search.add_argument("--provider", default=None)
    search.add_argument("-v", "--verbose", action="store_true")

    compare = sub.add_parser("compare", help="Show all four modes side-by-side for one query")
    compare.add_argument("query")
    compare.add_argument("--strategy", default="structural")
    compare.add_argument("--top-k", type=int, default=5)
    compare.add_argument("--family", default=None)
    compare.add_argument("--provider", default=None)
    compare.add_argument("-v", "--verbose", action="store_true")

    ev = sub.add_parser("eval", help="Golden-set Context Recall/Precision across modes")
    ev.add_argument("--strategy", default="structural")
    ev.add_argument("--provider", default=None)
    ev.add_argument("-v", "--verbose", action="store_true")

    demo = sub.add_parser("demo", help="Recruiter demos: paraphrase / exact ID / error code / Next API")
    demo.add_argument("--strategy", default="structural")
    demo.add_argument("--provider", default=None)
    demo.add_argument("-v", "--verbose", action="store_true")
    return parser


def _hits_json(hits) -> list[dict]:
    return [
        {
            "rank": h.rank,
            "score": round(h.score, 4),
            "source_id": h.source_id,
            "section_title": h.section_title,
            "family": h.family,
            "channels": h.channels,
            "preview": h.preview(),
        }
        for h in hits
    ]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.command == "search":
        rows = load_embedding_cache(cache_path(args.strategy))
        retriever = build_retriever(rows, provider=args.provider)
        hits = retriever.retrieve(
            args.query, mode=args.mode, family=args.family, top_k=args.top_k
        )
        print(json.dumps({"query": args.query, "mode": args.mode, "hits": _hits_json(hits)}, indent=2))
        return 0

    if args.command == "compare":
        rows = load_embedding_cache(cache_path(args.strategy))
        retriever = build_retriever(rows, provider=args.provider)
        out = {"query": args.query, "modes": {}}
        for mode in ("dense", "sparse", "hybrid", "hybrid_rerank"):
            hits = retriever.retrieve(
                args.query, mode=mode, family=args.family, top_k=args.top_k  # type: ignore[arg-type]
            )
            out["modes"][mode] = _hits_json(hits)
        print(json.dumps(out, indent=2))
        return 0

    if args.command == "eval":
        result = evaluate_modes(strategy=args.strategy, provider=args.provider)
        slim = {
            "winner": result["winner"],
            "ranking": result["ranking"],
            "metrics": {m: d["metrics"] for m, d in result["modes"].items()},
            "by_category": {
                m: d["by_category"] for m, d in result["modes"].items() if m in ("sparse", "hybrid_rerank")
            },
        }
        print(json.dumps(slim, indent=2))
        return 0

    if args.command == "demo":
        report = run_demos(strategy=args.strategy, provider=args.provider)
        print(json.dumps({"demos": report}, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
