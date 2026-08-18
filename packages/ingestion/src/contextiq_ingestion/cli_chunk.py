from __future__ import annotations

import argparse
import json
import logging
import sys

from contextiq_ingestion.chunking.runner import run_chunk_eval, run_chunking
from contextiq_ingestion.config import repo_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextiq-chunk",
        description="ContextIQ Phase 2 — chunking laboratory + golden-set recall eval",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Chunk all clean documents with one or more strategies")
    run_p.add_argument(
        "--strategy",
        action="append",
        dest="strategies",
        choices=["fixed", "structural", "semantic"],
        help="Strategy to run (repeatable). Default: all three.",
    )
    run_p.add_argument("--family", action="append", dest="families")
    run_p.add_argument("--chunk-size", type=int, default=500)
    run_p.add_argument("--overlap-ratio", type=float, default=0.15)
    run_p.add_argument("-v", "--verbose", action="store_true")

    eval_p = sub.add_parser("eval", help="Evaluate chunk strategies against eval/golden.jsonl")
    eval_p.add_argument(
        "--strategy",
        action="append",
        dest="strategies",
        choices=["fixed", "structural", "semantic"],
    )
    eval_p.add_argument(
        "--aws-only",
        action="store_true",
        help="Restrict retrieval corpus to aws+sst families (ablation)",
    )
    eval_p.add_argument("-v", "--verbose", action="store_true")

    lab_p = sub.add_parser("lab", help="Run chunking then eval (full laboratory)")
    lab_p.add_argument("--chunk-size", type=int, default=500)
    lab_p.add_argument("--overlap-ratio", type=float, default=0.15)
    lab_p.add_argument("--aws-only-eval", action="store_true")
    lab_p.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.command == "run":
        families = set(args.families) if args.families else None
        results = run_chunking(
            strategies=args.strategies,
            families=families,
            chunk_size=args.chunk_size,
            overlap_ratio=args.overlap_ratio,
        )
        summary = {name: len(chunks) for name, chunks in results.items()}
        print(json.dumps({"chunk_counts": summary}, indent=2))
        return 0

    if args.command == "eval":
        families = {"aws", "sst"} if args.aws_only else None
        comparison = run_chunk_eval(
            strategies=args.strategies,
            families_filter_chunks=families,
        )
        slim = {
            "winner": comparison["winner"],
            "ranking": comparison["ranking"],
            "metrics": {
                name: {
                    "metrics": data["metrics"],
                    "chunk_stats": data["chunk_stats"],
                    "chunk_count": data["chunk_count"],
                }
                for name, data in comparison["strategies"].items()
            },
        }
        print(json.dumps(slim, indent=2))
        return 0

    if args.command == "lab":
        run_chunking(chunk_size=args.chunk_size, overlap_ratio=args.overlap_ratio)
        families = {"aws", "sst"} if args.aws_only_eval else None
        comparison = run_chunk_eval(families_filter_chunks=families)
        # Also write AWS-only ablation when full-corpus eval runs
        if families is None:
            aws_path = repo_root() / "docs" / "eval-results" / "chunking-comparison-aws-only.json"
            run_chunk_eval(
                families_filter_chunks={"aws", "sst"},
                results_path=aws_path,
            )
        slim = {
            "winner": comparison["winner"],
            "ranking": comparison["ranking"],
            "metrics": {
                name: data["metrics"] for name, data in comparison["strategies"].items()
            },
        }
        print(json.dumps(slim, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
