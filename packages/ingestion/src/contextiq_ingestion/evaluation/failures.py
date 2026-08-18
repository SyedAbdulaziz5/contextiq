"""Load curated failure-analysis cases (Phase 12)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contextiq_ingestion.config import repo_root


def load_failure_cases(*, root: Path | None = None) -> dict[str, Any]:
    root = root or repo_root()
    path = root / "docs" / "eval-results" / "failure-cases.json"
    if not path.exists():
        return {
            "title": "Failure analysis",
            "cases": [],
            "error": f"Missing {path.name}. Add curated cases under docs/eval-results/.",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases") or []
    return {
        **data,
        "case_count": len(cases),
        "open_count": sum(1 for c in cases if c.get("status") == "open"),
        "mitigated_count": sum(1 for c in cases if c.get("status") == "mitigated"),
    }
