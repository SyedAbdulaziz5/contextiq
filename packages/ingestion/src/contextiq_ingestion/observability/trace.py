"""Phase 8 — structured end-to-end query traces."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from contextiq_ingestion.config import repo_root
from contextiq_ingestion.observability.cost import (
    estimate_cost_detail,
    estimate_cost_usd,
    pricing_catalog,
)

# Re-export pricing constants for older imports / docs
INPUT_USD_PER_M = 0.25
OUTPUT_USD_PER_M = 1.25


def estimate_tokens(text: str) -> int:
    return max(1, len((text or "").split()))


@dataclass
class StageTiming:
    name: str
    latency_ms: float


@dataclass
class QueryTrace:
    trace_id: str
    ts: float
    query: str
    rewritten_query: str | None
    route: str
    retrieval_skipped: bool
    stages: list[StageTiming] = field(default_factory=list)
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    retrieval_scores: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    answer_preview: str = ""
    confidence: str = "none"
    refused: bool = False
    grounded: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cost: dict[str, Any] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    generator: str = "local"
    feedback: str | None = None  # up | down | None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class TraceStore:
    """Append-only JSONL traces under local/ (gitignored)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (repo_root() / "local" / "traces.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, trace: QueryTrace) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trace.to_dict(), ensure_ascii=False) + "\n")

    def list(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line.strip()]
        return list(reversed(rows[-limit:]))

    def get(self, trace_id: str) -> dict[str, Any] | None:
        for row in self.list(limit=5000):
            if row.get("trace_id") == trace_id:
                return row
        return None

    def set_feedback(self, trace_id: str, feedback: str) -> bool:
        if feedback not in {"up", "down"}:
            raise ValueError("feedback must be up|down")
        if not self.path.exists():
            return False
        lines = self.path.read_text(encoding="utf-8").splitlines()
        updated = False
        out: list[str] = []
        for line in lines:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("trace_id") == trace_id:
                row["feedback"] = feedback
                updated = True
            out.append(json.dumps(row, ensure_ascii=False))
        if updated:
            self.path.write_text("\n".join(out) + "\n", encoding="utf-8")
        return updated

    def stats(self) -> dict[str, Any]:
        rows = self.list(limit=5000)
        if not rows:
            return {
                "n": 0,
                "avg_latency_ms": 0,
                "avg_cost_usd": 0,
                "refusal_rate": 0,
                "feedback": {"up": 0, "down": 0, "none": 0},
            }
        n = len(rows)
        avg_lat = sum(r.get("total_latency_ms") or 0 for r in rows) / n
        avg_cost = sum(r.get("cost_usd") or 0 for r in rows) / n
        refusals = sum(1 for r in rows if r.get("refused"))
        fb = {"up": 0, "down": 0, "none": 0}
        for r in rows:
            key = r.get("feedback") or "none"
            if key not in fb:
                key = "none"
            fb[key] += 1
        stage_avgs: dict[str, list[float]] = {}
        for r in rows:
            for s in r.get("stages") or []:
                stage_avgs.setdefault(s["name"], []).append(float(s["latency_ms"]))
        return {
            "n": n,
            "avg_latency_ms": round(avg_lat, 1),
            "avg_cost_usd": round(avg_cost, 6),
            "refusal_rate": round(refusals / n, 4),
            "feedback": fb,
            "avg_stage_ms": {
                k: round(sum(v) / len(v), 1) for k, v in stage_avgs.items()
            },
        }


_STORE: TraceStore | None = None


def get_trace_store() -> TraceStore:
    global _STORE
    if _STORE is None:
        _STORE = TraceStore()
    return _STORE


class Timer:
    def __init__(self) -> None:
        self.t0 = time.perf_counter()

    def ms(self) -> float:
        return round((time.perf_counter() - self.t0) * 1000, 2)


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]
