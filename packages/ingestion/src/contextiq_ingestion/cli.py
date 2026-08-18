from __future__ import annotations

import argparse
import json
import logging
import sys

from contextiq_ingestion.pipeline import run_ingestion, smoke_parse_formats
from contextiq_ingestion.store import summarize_docs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextiq-ingest",
        description="ContextIQ Phase 1 — fetch docs, preserve structure, write clean JSON + catalog",
    )
    parser.add_argument(
        "--family",
        action="append",
        dest="families",
        help="Filter by family (nextjs, fastapi, aws, sst). Repeatable.",
    )
    parser.add_argument(
        "--source-id",
        action="append",
        dest="source_ids",
        help="Ingest only these source ids. Repeatable.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max sources to ingest")
    parser.add_argument("--force-fetch", action="store_true", help="Re-download even if raw file exists")
    parser.add_argument("--skip-catalog", action="store_true", help="Do not write SQLite catalog")
    parser.add_argument("--smoke", action="store_true", help="Run offline parser smoke checks and exit")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.smoke:
        result = smoke_parse_formats()
        print(json.dumps(result, indent=2))
        return 0 if all(result.values()) else 1

    families = set(args.families) if args.families else None
    source_ids = set(args.source_ids) if args.source_ids else None

    ingest = run_ingestion(
        families=families,
        source_ids=source_ids,
        limit=args.limit,
        force_fetch=args.force_fetch,
        skip_catalog=args.skip_catalog,
    )
    summary = summarize_docs(ingest.succeeded)
    print(json.dumps({"summary": summary, "failed": ingest.failed}, indent=2))
    if ingest.failed and not ingest.succeeded:
        return 2
    if ingest.failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
