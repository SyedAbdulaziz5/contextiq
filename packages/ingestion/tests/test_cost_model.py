from __future__ import annotations

from contextiq_ingestion.evaluation.cost_tradeoffs import load_cost_tradeoffs
from contextiq_ingestion.observability.cost import estimate_cost_detail, estimate_cost_usd


def test_local_generators_zero():
    assert estimate_cost_usd(input_tokens=100, output_tokens=50, generator="ollama:llama3.2:1b") == 0.0
    assert estimate_cost_usd(input_tokens=100, output_tokens=50, generator="local-extractive") == 0.0


def test_bedrock_haiku_example():
    detail = estimate_cost_detail(input_tokens=312, output_tokens=37, generator="bedrock")
    assert detail.pricing_key == "bedrock_haiku"
    assert detail.billing == "per_token"
    assert abs(detail.usd - 0.00012425) < 1e-8
    assert "Haiku" in detail.label


def test_load_cost_tradeoffs():
    data = load_cost_tradeoffs()
    assert len(data.get("comparisons") or []) >= 3
    assert data.get("pricing_live")
