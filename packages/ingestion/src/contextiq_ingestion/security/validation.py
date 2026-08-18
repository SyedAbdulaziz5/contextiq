from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


class ValidationError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class Limits:
    max_query_chars: int
    max_history_turns: int
    max_history_turn_chars: int
    max_top_k: int


def load_limits() -> Limits:
    return Limits(
        max_query_chars=int(os.getenv("CONTEXTIQ_MAX_QUERY_CHARS") or "2000"),
        max_history_turns=int(os.getenv("CONTEXTIQ_MAX_HISTORY_TURNS") or "20"),
        max_history_turn_chars=int(os.getenv("CONTEXTIQ_MAX_HISTORY_TURN_CHARS") or "2000"),
        max_top_k=int(os.getenv("CONTEXTIQ_MAX_TOP_K") or "20"),
    )


def validate_query_body(body: dict[str, Any], limits: Limits | None = None) -> dict[str, Any]:
    """
    Normalize and validate a /query or /query/stream JSON body.
    Returns a cleaned dict with keys: query, history (raw list), top_k, family.
    """
    lim = limits or load_limits()
    query_text = str(body.get("query") or body.get("question") or "").strip()
    if not query_text:
        raise ValidationError("query required")
    if len(query_text) > lim.max_query_chars:
        raise ValidationError(
            f"query exceeds max length ({lim.max_query_chars} characters)"
        )

    raw_history = body.get("history") or []
    if not isinstance(raw_history, list):
        raise ValidationError("history must be a list")
    if len(raw_history) > lim.max_history_turns:
        raise ValidationError(
            f"history exceeds max turns ({lim.max_history_turns})"
        )
    for item in raw_history:
        content = item if isinstance(item, str) else str((item or {}).get("content") or "")
        if len(content) > lim.max_history_turn_chars:
            raise ValidationError(
                f"history turn exceeds max length ({lim.max_history_turn_chars} characters)"
            )

    top_k_raw = body.get("top_k")
    top_k = int(top_k_raw) if top_k_raw is not None else 6
    if top_k < 1 or top_k > lim.max_top_k:
        raise ValidationError(f"top_k must be between 1 and {lim.max_top_k}")

    family = body.get("family")
    if family is not None:
        family = str(family)[:64]

    return {
        "query": query_text,
        "history": raw_history,
        "top_k": top_k,
        "family": family,
    }
