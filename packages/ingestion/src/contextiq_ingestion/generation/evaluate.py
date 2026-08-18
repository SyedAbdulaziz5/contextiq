from __future__ import annotations

import json
from pathlib import Path

from contextiq_ingestion.generation.pipeline import GroundedChatPipeline
from contextiq_ingestion.generation.prompts import REFUSAL_TEXT

REPO_ROOT = Path(__file__).resolve().parents[5]
GOLDEN_PATH = REPO_ROOT / "eval" / "golden.jsonl"


def load_golden(path: Path | None = None) -> list[dict]:
    p = path or GOLDEN_PATH
    rows: list[dict] = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def is_refusal_answer(answer: str, *, insufficient: bool) -> bool:
    if insufficient:
        return True
    a = answer.lower()
    markers = [
        "don't have enough information",
        "do not have enough information",
        "not enough information",
        "cannot answer",
        "can't answer",
        "outside the",
        "not in the",
        REFUSAL_TEXT.lower(),
    ]
    return any(m in a for m in markers)


def eval_refusal(
    pipeline: GroundedChatPipeline,
    *,
    golden_path: Path | None = None,
) -> dict:
    """Measure refusal accuracy on unanswerable golden questions."""
    rows = [r for r in load_golden(golden_path) if r.get("category") == "unanswerable"]
    correct = 0
    details: list[dict] = []
    for row in rows:
        result = pipeline.ask(row["question"], top_k=6)
        refused = is_refusal_answer(
            result.answer.answer,
            insufficient=result.answer.insufficient_context,
        )
        ok = refused
        if ok:
            correct += 1
        details.append(
            {
                "id": row["id"],
                "question": row["question"],
                "refused": refused,
                "correct": ok,
                "confidence": result.answer.confidence,
                "preview": (result.answer.display_answer or result.answer.answer)[:160],
            }
        )
    total = len(rows) or 1
    return {
        "metric": "refusal_accuracy",
        "total": len(rows),
        "correct": correct,
        "accuracy": round(correct / total, 4),
        "details": details,
    }


def eval_grounded_smoke(
    pipeline: GroundedChatPipeline,
    *,
    golden_path: Path | None = None,
    limit: int = 8,
) -> dict:
    """Quick check: answerable factual Qs should not refuse and should cite."""
    rows = [
        r
        for r in load_golden(golden_path)
        if r.get("category") in {"factual", "keyword", "table"}
        and r.get("expected_source_ids")
    ][:limit]
    cited = 0
    answered = 0
    details: list[dict] = []
    for row in rows:
        result = pipeline.ask(row["question"], top_k=6)
        refused = result.answer.insufficient_context or is_refusal_answer(
            result.answer.answer, insufficient=False
        )
        has_cite = bool(result.answer.citations) or bool(
            "[" in (result.answer.display_answer or "")
        )
        if not refused:
            answered += 1
        if has_cite and not refused:
            cited += 1
        details.append(
            {
                "id": row["id"],
                "refused": refused,
                "has_citation": has_cite,
                "preview": (result.answer.display_answer or result.answer.answer)[:160],
            }
        )
    n = len(rows) or 1
    return {
        "metric": "grounded_smoke",
        "total": len(rows),
        "answered": answered,
        "cited": cited,
        "answer_rate": round(answered / n, 4),
        "cite_rate": round(cited / n, 4),
        "details": details,
    }
