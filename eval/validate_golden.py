#!/usr/bin/env python3
"""Validate eval/golden.jsonl against schema rules and corpus/sources.json."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).resolve().parent / "golden.jsonl"
SOURCES = ROOT / "corpus" / "sources.json"

CATEGORIES = {
    "factual",
    "keyword",
    "multi_hop",
    "unanswerable",
    "ambiguous",
    "table",
    "edge_case",
}
ID_RE = re.compile(r"^q\d{3}$")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not GOLDEN.exists():
        fail(f"missing {GOLDEN}")
    if not SOURCES.exists():
        fail(f"missing {SOURCES}")

    source_ids = {s["id"] for s in json.loads(SOURCES.read_text())["sources"]}
    rows: list[dict] = []
    for i, line in enumerate(GOLDEN.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            fail(f"line {i}: invalid JSON ({e})")

    if len(rows) < 50:
        fail(f"need at least 50 golden items, found {len(rows)}")

    seen_ids: set[str] = set()
    cat_counts: Counter[str] = Counter()

    for i, row in enumerate(rows, start=1):
        for key in ("id", "question", "expected_answer", "expected_source_ids", "category"):
            if key not in row:
                fail(f"row {i}: missing field '{key}'")

        rid = row["id"]
        if not ID_RE.match(rid):
            fail(f"row {i}: id '{rid}' must match qNNN")
        if rid in seen_ids:
            fail(f"row {i}: duplicate id '{rid}'")
        seen_ids.add(rid)

        cat = row["category"]
        if cat not in CATEGORIES:
            fail(f"row {i}: unknown category '{cat}'")
        cat_counts[cat] += 1

        sources = row["expected_source_ids"]
        if not isinstance(sources, list):
            fail(f"row {i}: expected_source_ids must be a list")

        if cat == "unanswerable" and len(sources) != 0:
            fail(f"row {i}: unanswerable must have empty expected_source_ids")
        if cat == "multi_hop" and len(sources) < 2:
            fail(f"row {i}: multi_hop needs >= 2 expected_source_ids")

        for sid in sources:
            if sid not in source_ids:
                fail(f"row {i}: unknown source_id '{sid}' — add it to corpus/sources.json first")

        if row.get("difficulty") not in (None, "easy", "medium", "hard"):
            fail(f"row {i}: invalid difficulty")

    missing_cats = CATEGORIES - set(cat_counts)
    if missing_cats:
        fail(f"missing required categories: {sorted(missing_cats)}")

    print(f"OK — {len(rows)} golden records")
    print("category counts:")
    for cat in sorted(cat_counts):
        print(f"  {cat:14} {cat_counts[cat]}")
    print(f"unique source_ids referenced: {len({s for r in rows for s in r['expected_source_ids']})}")


if __name__ == "__main__":
    main()
