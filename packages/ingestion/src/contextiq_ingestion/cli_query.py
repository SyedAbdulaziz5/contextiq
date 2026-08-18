from __future__ import annotations

import argparse
import json
import logging
import sys

from contextiq_ingestion.embeddings.cache import cache_path, load_embedding_cache
from contextiq_ingestion.query.evaluate import run_all_query_evals
from contextiq_ingestion.query.hyde import get_hyde_generator
from contextiq_ingestion.query.pipeline import build_query_pipeline
from contextiq_ingestion.query.rewriter import QueryRewriter, Turn
from contextiq_ingestion.query.router import QueryRouter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextiq-query",
        description="ContextIQ Phase 5 — query routing, rewriting, HyDE (+ A/B tests)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    route = sub.add_parser("route", help="Classify a query (greeting/meta/calc/clarify/rag)")
    route.add_argument("query")
    route.add_argument("-v", "--verbose", action="store_true")

    rewrite = sub.add_parser("rewrite", help="Rewrite using optional conversation history")
    rewrite.add_argument("query")
    rewrite.add_argument(
        "--history",
        action="append",
        default=[],
        help="Prior USER turns, oldest first. Repeatable.",
    )
    rewrite.add_argument("-v", "--verbose", action="store_true")

    hyde = sub.add_parser("hyde", help="Generate a hypothetical document for a query")
    hyde.add_argument("query")
    hyde.add_argument("--provider", default=None, help="template|bedrock")
    hyde.add_argument("-v", "--verbose", action="store_true")

    ask = sub.add_parser("ask", help="Full pipeline: route → rewrite → (HyDE) → retrieve")
    ask.add_argument("query")
    ask.add_argument("--history", action="append", default=[])
    ask.add_argument("--dense-strategy", choices=["raw", "hyde"], default="raw")
    ask.add_argument("--mode", default="hybrid_rerank", choices=["dense", "sparse", "hybrid", "hybrid_rerank"])
    ask.add_argument("--strategy", default="structural")
    ask.add_argument("--family", default=None)
    ask.add_argument("--top-k", type=int, default=5)
    ask.add_argument("--provider", default=None)
    ask.add_argument("--hyde-provider", default=None)
    ask.add_argument("--force-rag", action="store_true")
    ask.add_argument("-v", "--verbose", action="store_true")

    ab = sub.add_parser("ab-hyde", help="A/B test raw vs HyDE dense channel on golden set")
    ab.add_argument("--strategy", default="structural")
    ab.add_argument("--provider", default=None)
    ab.add_argument("--hyde-provider", default=None)
    ab.add_argument("-v", "--verbose", action="store_true")

    ev = sub.add_parser("eval", help="Router + rewriter fixtures + HyDE A/B")
    ev.add_argument("--strategy", default="structural")
    ev.add_argument("--provider", default=None)
    ev.add_argument("--hyde-provider", default=None)
    ev.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.command == "route":
        decision = QueryRouter().route(args.query)
        print(
            json.dumps(
                {
                    "query": args.query,
                    "route": decision.route.value,
                    "confidence": decision.confidence,
                    "reason": decision.reason,
                    "reply": decision.reply,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "rewrite":
        history = [Turn(role="user", content=h) for h in args.history]
        result = QueryRewriter().rewrite(args.query, history)
        print(
            json.dumps(
                {
                    "original": result.original,
                    "rewritten": result.rewritten,
                    "changed": result.changed,
                    "reason": result.reason,
                    "history_used": result.history_used,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "hyde":
        result = get_hyde_generator(args.provider).generate(args.query)
        print(
            json.dumps(
                {
                    "query": result.query,
                    "method": result.method,
                    "hypothetical_document": result.hypothetical_document,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "ask":
        rows = load_embedding_cache(cache_path(args.strategy))
        pipeline = build_query_pipeline(
            rows, provider=args.provider, hyde_provider=args.hyde_provider
        )
        history = [Turn(role="user", content=h) for h in args.history]
        result = pipeline.run(
            args.query,
            history=history,
            dense_strategy=args.dense_strategy,
            retrieval_mode=args.mode,
            family=args.family,
            top_k=args.top_k,
            force_rag=args.force_rag,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    if args.command in {"ab-hyde", "eval"}:
        report = run_all_query_evals(
            strategy=args.strategy,
            provider=args.provider,
            hyde_provider=args.hyde_provider,
        )
        if args.command == "ab-hyde":
            print(json.dumps(report["hyde_ab"], indent=2))
        else:
            slim = {
                "router_accuracy": report["router"]["accuracy"],
                "rewriter_accuracy": report["rewriter"]["accuracy"],
                "hyde_ab": report["hyde_ab"],
            }
            print(json.dumps(slim, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
