"""Shared structured JSON parsing for grounded generators."""

from __future__ import annotations

import json
import re
from typing import Any

from contextiq_ingestion.generation.models import (
    Citation,
    GroundedAnswer,
    SourceRef,
    answer_with_numeric_chips,
)
from contextiq_ingestion.generation.prompts import REFUSAL_TEXT


def parse_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {
                "answer": REFUSAL_TEXT,
                "citations": [],
                "confidence": "none",
                "insufficient_context": True,
            }
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {
                "answer": REFUSAL_TEXT,
                "citations": [],
                "confidence": "none",
                "insufficient_context": True,
            }


def grounded_from_parsed(
    parsed: dict[str, Any],
    refs: list[SourceRef],
    *,
    generator: str,
) -> GroundedAnswer:
    by_sid = {r.source_id: r for r in refs}
    citations: list[Citation] = []
    for raw in parsed.get("citations") or []:
        sid = str(raw.get("source_id", "")).upper()
        if not sid.startswith("S"):
            sid = f"S{sid}" if sid.isdigit() else sid
        ref = by_sid.get(sid)
        citations.append(
            Citation(
                claim_span=str(raw.get("claim_span") or "")[:200],
                source_id=sid,
                chunk_key=ref.chunk_key if ref else None,
                doc_source_id=ref.doc_source_id if ref else None,
                title=ref.title if ref else None,
                section_title=ref.section_title if ref else None,
                source_url=ref.source_url if ref else None,
                snippet=ref.snippet[:280] if ref else None,
            )
        )
    answer = str(parsed.get("answer") or REFUSAL_TEXT)
    insufficient = bool(parsed.get("insufficient_context"))
    confidence = parsed.get("confidence") or ("none" if insufficient else "medium")
    if confidence not in {"high", "medium", "low", "none"}:
        confidence = "medium"
    grounded = GroundedAnswer(
        answer=answer,
        citations=citations,
        confidence=confidence,  # type: ignore[arg-type]
        insufficient_context=insufficient,
        sources=refs,
        meta={"generator": generator},
    )
    grounded.display_answer = answer_with_numeric_chips(answer, citations)
    return grounded
