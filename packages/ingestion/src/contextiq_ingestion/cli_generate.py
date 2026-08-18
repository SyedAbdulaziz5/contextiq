from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from contextiq_ingestion.generation.evaluate import eval_grounded_smoke, eval_refusal
from contextiq_ingestion.generation.pipeline import build_chat_pipeline
from contextiq_ingestion.query.rewriter import Turn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextiq-generate",
        description="ContextIQ Phase 6 — grounded generation + citations",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="Route → retrieve → grounded answer")
    ask.add_argument("query")
    ask.add_argument("--history", action="append", default=[])
    ask.add_argument("--strategy", default="structural")
    ask.add_argument("--family", default=None)
    ask.add_argument("--top-k", type=int, default=6)
    ask.add_argument("--embed-provider", default=None)
    ask.add_argument("--generator", default=None, help="local|bedrock")
    ask.add_argument("-v", "--verbose", action="store_true")

    demo = sub.add_parser("demo", help="Print answer + citation mapping")
    demo.add_argument("query")
    demo.add_argument("--strategy", default="structural")
    demo.add_argument("--generator", default=None)
    demo.add_argument("--embed-provider", default=None)
    demo.add_argument("-v", "--verbose", action="store_true")

    ev = sub.add_parser("eval", help="Refusal accuracy + grounded smoke")
    ev.add_argument("--strategy", default="structural")
    ev.add_argument("--generator", default=None)
    ev.add_argument("--embed-provider", default=None)
    ev.add_argument("--out", default=None, help="Write JSON results path")
    ev.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    pipeline = build_chat_pipeline(
        strategy=args.strategy if hasattr(args, "strategy") else "structural",
        embed_provider=getattr(args, "embed_provider", None),
        generator=getattr(args, "generator", None),
    )

    if args.command == "ask":
        history = [Turn(role="user", content=h) for h in args.history]
        result = pipeline.ask(
            args.query,
            history=history,
            family=args.family,
            top_k=args.top_k,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    if args.command == "demo":
        result = pipeline.ask(args.query)
        print("=== Answer ===")
        print(result.answer.display_answer or result.answer.answer)
        print()
        print(f"confidence={result.answer.confidence} refused={result.answer.insufficient_context}")
        print()
        if result.answer.citations:
            print("=== Citations ===")
            for c in result.answer.citations:
                print(f"  [{c.source_id}] {c.title} — {c.section_title}")
                print(f"       span: {c.claim_span}")
                if c.source_url:
                    print(f"       url:  {c.source_url}")
        return 0

    if args.command == "eval":
        refusal = eval_refusal(pipeline)
        smoke = eval_grounded_smoke(pipeline)
        out = {
            "refusal": {k: v for k, v in refusal.items() if k != "details"},
            "smoke": {k: v for k, v in smoke.items() if k != "details"},
            "refusal_details": refusal["details"],
            "smoke_details": smoke["details"],
        }
        text = json.dumps(out, indent=2)
        print(text)
        if args.out:
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n")
        return 0 if refusal["accuracy"] >= 0.7 else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
