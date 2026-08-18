"""Token cost estimation with explicit pricing assumptions (Phase 16)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# Published Bedrock Claude 3 Haiku on-demand list prices (USD / 1M tokens).
# Source note: AWS Bedrock pricing page — update if the project switches models.
BEDROCK_HAIKU_INPUT_USD_PER_M = 0.25
BEDROCK_HAIKU_OUTPUT_USD_PER_M = 1.25

PRICING_TABLE: dict[str, dict[str, Any]] = {
    "extractive": {
        "label": "Local extractive",
        "billing": "none",
        "input_usd_per_m": 0.0,
        "output_usd_per_m": 0.0,
        "note": "No LLM API — answers copied from retrieved context. $0 API cost.",
    },
    "ollama": {
        "label": "Ollama (local)",
        "billing": "none",
        "input_usd_per_m": 0.0,
        "output_usd_per_m": 0.0,
        "note": "Runs on your machine. $0 API cost; electricity/GPU not metered here.",
    },
    "bedrock_haiku": {
        "label": "Bedrock Claude 3 Haiku",
        "billing": "per_token",
        "input_usd_per_m": BEDROCK_HAIKU_INPUT_USD_PER_M,
        "output_usd_per_m": BEDROCK_HAIKU_OUTPUT_USD_PER_M,
        "note": "Optional cloud path. List price USD/1M tokens (input 0.25 / output 1.25).",
    },
}


def classify_generator(generator: str | None) -> str:
    g = (generator or "").lower()
    if not g or g.startswith("local") or g in {"extractive", "router", "local-extractive"}:
        return "extractive"
    if g.startswith("ollama"):
        return "ollama"
    if "bedrock" in g or "claude" in g or g.startswith("amazon"):
        return "bedrock_haiku"
    # Unknown paid-looking generator: treat as Bedrock Haiku table for visibility
    if g not in {"hash", "sbert"}:
        return "bedrock_haiku"
    return "extractive"


@dataclass
class CostEstimate:
    usd: float
    pricing_key: str
    label: str
    billing: str
    note: str
    input_tokens: int
    output_tokens: int
    input_usd_per_m: float
    output_usd_per_m: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def estimate_cost_detail(
    *,
    input_tokens: int,
    output_tokens: int,
    generator: str | None,
) -> CostEstimate:
    key = classify_generator(generator)
    row = PRICING_TABLE[key]
    usd = (
        input_tokens * float(row["input_usd_per_m"])
        + output_tokens * float(row["output_usd_per_m"])
    ) / 1_000_000
    return CostEstimate(
        usd=round(usd, 8),
        pricing_key=key,
        label=str(row["label"]),
        billing=str(row["billing"]),
        note=str(row["note"]),
        input_tokens=int(input_tokens),
        output_tokens=int(output_tokens),
        input_usd_per_m=float(row["input_usd_per_m"]),
        output_usd_per_m=float(row["output_usd_per_m"]),
    )


def estimate_cost_usd(*, input_tokens: int, output_tokens: int, generator: str) -> float:
    return estimate_cost_detail(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        generator=generator,
    ).usd


def pricing_catalog() -> list[dict[str, Any]]:
    return [{"key": k, **v} for k, v in PRICING_TABLE.items()]
