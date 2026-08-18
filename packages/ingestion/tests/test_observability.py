from __future__ import annotations

import json
from pathlib import Path

from contextiq_ingestion.observability.trace import TraceStore, estimate_cost_usd, estimate_tokens


def test_estimate_tokens_and_cost():
    assert estimate_tokens("one two three") == 3
    assert estimate_cost_usd(input_tokens=1000, output_tokens=1000, generator="local") == 0.0
    assert estimate_cost_usd(input_tokens=1_000_000, output_tokens=0, generator="bedrock") > 0


def test_trace_store_roundtrip(tmp_path: Path):
    from contextiq_ingestion.observability.trace import QueryTrace, StageTiming
    import time

    store = TraceStore(path=tmp_path / "traces.jsonl")
    tr = QueryTrace(
        trace_id="abc123",
        ts=time.time(),
        query="What is Lambda timeout?",
        rewritten_query="What is Lambda timeout?",
        route="rag",
        retrieval_skipped=False,
        stages=[StageTiming("retrieve", 12.5)],
        refused=False,
        grounded=True,
        total_latency_ms=40.0,
    )
    store.append(tr)
    rows = store.list(limit=10)
    assert rows[0]["trace_id"] == "abc123"
    assert store.set_feedback("abc123", "up")
    assert store.get("abc123")["feedback"] == "up"
    stats = store.stats()
    assert stats["n"] == 1
    assert stats["feedback"]["up"] == 1
