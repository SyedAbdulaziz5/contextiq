"""Load cost/quality tradeoff artifacts (Phase 16)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contextiq_ingestion.config import repo_root
from contextiq_ingestion.observability.cost import pricing_catalog


def load_cost_tradeoffs(*, root: Path | None = None) -> dict[str, Any]:
    root = root or repo_root()
    path = root / "docs" / "eval-results" / "cost-tradeoffs.json"
    if not path.exists():
        return {
            "title": "Quality · latency · cost tradeoffs",
            "comparisons": [],
            "pricing": pricing_catalog(),
            "error": f"Missing {path.name}",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    # Always attach live pricing catalog (single source of truth in code)
    data["pricing_live"] = pricing_catalog()
    data["assumptions_doc"] = data.get("assumptions_doc") or "docs/cost-model.md"
    return data
