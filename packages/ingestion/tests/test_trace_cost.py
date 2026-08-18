from __future__ import annotations

from contextiq_ingestion.observability.trace import estimate_cost_usd


def test_ollama_and_local_cost_zero():
    assert estimate_cost_usd(input_tokens=100, output_tokens=50, generator="ollama:llama3.2:1b") == 0.0
    assert estimate_cost_usd(input_tokens=100, output_tokens=50, generator="local-extractive") == 0.0


def test_bedrock_cost_nonzero():
    cost = estimate_cost_usd(input_tokens=1_000_000, output_tokens=0, generator="bedrock")
    assert cost == 0.25
