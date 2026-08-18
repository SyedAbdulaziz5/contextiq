from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from contextiq_ingestion.evaluation.ci_gate import promote_baseline, run_gate
from contextiq_ingestion.evaluation.suite import (
    publish_results,
    run_experiment_matrix,
    run_rag_suite,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextiq-eval",
        description="ContextIQ — RAG metrics, experiments, CI gate",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Full suite + experiments + write docs/eval-results")
    run.add_argument("--strategy", default="structural")
    run.add_argument("--mode", default="hybrid_rerank")
    run.add_argument("--top-k", type=int, default=5)
    run.add_argument("--generator", default="local")
    run.add_argument("--limit", type=int, default=None, help="Limit golden rows (debug)")
    run.add_argument("--skip-experiments", action="store_true")
    run.add_argument("-v", "--verbose", action="store_true")

    metrics = sub.add_parser("metrics", help="Headline metrics only")
    metrics.add_argument("--strategy", default="structural")
    metrics.add_argument("--top-k", type=int, default=5)
    metrics.add_argument("--generator", default="local")
    metrics.add_argument("--limit", type=int, default=None)
    metrics.add_argument("-v", "--verbose", action="store_true")

    exp = sub.add_parser("experiments", help="Chunk strategy × hybrid comparison table")
    exp.add_argument("--top-k", type=int, default=5)
    exp.add_argument("-v", "--verbose", action="store_true")

    gate = sub.add_parser(
        "gate",
        help="CI gate: compare docs/eval-results vs eval/ci/baseline (+ floors)",
    )
    gate.add_argument("--current", type=Path, default=None)
    gate.add_argument("--baseline", type=Path, default=None)
    gate.add_argument("--thresholds", type=Path, default=None)
    gate.add_argument("--pr-label", default="PR")
    gate.add_argument("--baseline-label", default="main")
    gate.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write markdown report path (e.g. eval/ci/gate-report.md)",
    )
    gate.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write machine-readable gate JSON",
    )
    gate.add_argument("-v", "--verbose", action="store_true")

    promote = sub.add_parser(
        "promote-baseline",
        help="Copy current rag-metrics.json into eval/ci/baseline.json (after green main)",
    )
    promote.add_argument("--current", type=Path, default=None)
    promote.add_argument("--baseline", type=Path, default=None)
    promote.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.command == "metrics":
        suite = run_rag_suite(
            strategy=args.strategy,
            top_k=args.top_k,
            generator=args.generator,
            limit=args.limit,
        )
        print(json.dumps({k: v for k, v in suite.items() if k != "details"}, indent=2))
        return 0

    if args.command == "experiments":
        experiments = run_experiment_matrix(top_k=args.top_k)
        print(json.dumps(experiments, indent=2))
        return 0

    if args.command == "run":
        suite = run_rag_suite(
            strategy=args.strategy,
            mode=args.mode,
            top_k=args.top_k,
            generator=args.generator,
            limit=args.limit,
        )
        experiments = (
            {"suite": "experiments", "table": [], "winner": None, "experiments": []}
            if args.skip_experiments
            else run_experiment_matrix(top_k=args.top_k)
        )
        paths = publish_results(suite, experiments)
        summary = {
            "metrics_pct": suite["metrics_pct"],
            "queries_evaluated": suite["queries_evaluated"],
            "experiments": experiments.get("table"),
            "winner": experiments.get("winner"),
            "wrote": {k: str(v) for k, v in paths.items()},
        }
        print(json.dumps(summary, indent=2))
        refusal = suite["metrics"].get("refusal_accuracy")
        faith = suite["metrics"].get("faithfulness")
        if refusal is not None and refusal < 0.8:
            return 1
        if faith is not None and faith < 0.5:
            return 1
        return 0

    if args.command == "gate":
        try:
            gate_result, md = run_gate(
                current_path=args.current,
                baseline_path=args.baseline,
                thresholds_path=args.thresholds,
                pr_label=args.pr_label,
                baseline_label=args.baseline_label,
            )
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(md)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(md + "\n", encoding="utf-8")
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(gate_result, indent=2) + "\n")
        return 0 if gate_result["passed"] else 1

    if args.command == "promote-baseline":
        path = promote_baseline(current_path=args.current, baseline_path=args.baseline)
        print(f"Updated baseline → {path}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
