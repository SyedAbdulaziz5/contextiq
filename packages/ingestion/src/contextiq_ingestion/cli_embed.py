from __future__ import annotations

import argparse
import json
import logging
import sys

from contextiq_ingestion.embeddings.db import PostgresStore, get_database_url
from contextiq_ingestion.embeddings.pipeline import run_dense_eval, run_search, run_upsert


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextiq-embed",
        description="ContextIQ Phase 3 — embeddings, pgvector storage, dense/sparse search",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init-db", help="Apply SQL schema to DATABASE_URL")
    init_p.add_argument("-v", "--verbose", action="store_true")

    up = sub.add_parser("upsert", help="Embed chunks and write cache (+ Postgres if configured)")
    up.add_argument("--strategy", default="structural", choices=["fixed", "structural", "semantic"])
    up.add_argument("--provider", default=None, help="sbert|hash|bedrock (default: sbert)")
    up.add_argument("--skip-postgres", action="store_true")
    up.add_argument("--batch-size", type=int, default=32)
    up.add_argument("-v", "--verbose", action="store_true")

    search = sub.add_parser("search", help="Dense or sparse retrieval demo")
    search.add_argument("query")
    search.add_argument("--strategy", default="structural")
    search.add_argument("--top-k", type=int, default=5)
    search.add_argument("--family", default=None)
    search.add_argument("--mode", choices=["dense", "sparse"], default="dense")
    search.add_argument("--provider", default=None)
    search.add_argument("--backend", choices=["auto", "memory", "postgres"], default="auto")
    search.add_argument("-v", "--verbose", action="store_true")

    ev = sub.add_parser("eval", help="Dense Source Recall@k vs golden.jsonl")
    ev.add_argument("--strategy", default="structural")
    ev.add_argument("--provider", default=None)
    ev.add_argument("--backend", choices=["auto", "memory", "postgres"], default="auto")
    ev.add_argument("-v", "--verbose", action="store_true")

    st = sub.add_parser("stats", help="Show Postgres table counts")
    st.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.command == "init-db":
        if not get_database_url():
            print(
                json.dumps(
                    {
                        "error": "DATABASE_URL not set",
                        "hint": "docker compose -f infra/docker-compose.yml up -d && "
                        "export DATABASE_URL=postgresql://contextiq:contextiq@localhost:5433/contextiq",
                    },
                    indent=2,
                )
            )
            return 2
        store = PostgresStore()
        store.init_schema()
        print(json.dumps({"ok": True, "stats": store.stats()}, indent=2))
        return 0

    if args.command == "upsert":
        result = run_upsert(
            strategy=args.strategy,
            provider=args.provider,
            skip_postgres=args.skip_postgres,
            batch_size=args.batch_size,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "search":
        hits = run_search(
            args.query,
            strategy=args.strategy,
            top_k=args.top_k,
            family=args.family,
            mode=args.mode,
            provider=args.provider,
            backend=args.backend,
        )
        print(json.dumps({"query": args.query, "mode": args.mode, "hits": hits}, indent=2))
        return 0

    if args.command == "eval":
        result = run_dense_eval(
            strategy=args.strategy,
            provider=args.provider,
            backend=args.backend,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "stats":
        if not get_database_url():
            print(json.dumps({"error": "DATABASE_URL not set"}, indent=2))
            return 2
        print(json.dumps(PostgresStore().stats(), indent=2))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
