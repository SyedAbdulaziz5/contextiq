from __future__ import annotations

from contextiq_ingestion.evaluation.metrics import (
    answer_relevancy,
    claim_supported,
    context_precision,
    context_recall,
    faithfulness,
    split_claims,
)
from contextiq_ingestion.retrieval.types import RankedHit


def _hit(source_id: str, content: str) -> RankedHit:
    return RankedHit(
        chunk_key=f"{source_id}#0",
        source_id=source_id,
        content=content,
        score=1.0,
        rank=1,
    )


def test_context_precision_recall():
    hits = [
        _hit("aws-lambda-limits", "timeout 900"),
        _hit("other-doc", "unrelated"),
    ]
    assert context_precision(hits, ["aws-lambda-limits"]) == 0.5
    assert context_recall(hits, ["aws-lambda-limits"]) == 1.0
    assert context_recall(hits, ["aws-lambda-limits", "missing"]) == 0.5


def test_faithfulness_supported():
    context = ["Lambda function timeout is 900 seconds (15 minutes)."]
    answer = "The maximum Lambda timeout is 900 seconds."
    assert faithfulness(answer, context) == 1.0


def test_faithfulness_hallucination():
    context = ["Lambda memory ranges from 128 MB to 10,240 MB."]
    answer = "Lambda can run for 48 hours without stopping."
    assert faithfulness(answer, context) < 0.5


def test_refusal_vacuous_faithfulness():
    assert faithfulness("I don't know.", [], refused=True) == 1.0


def test_claim_split_and_support():
    claims = split_claims("Server Components render on the server. They can fetch data.")
    assert len(claims) >= 2
    assert claim_supported(
        "Server Components render on the server",
        "Server Components are rendered on the server by default.",
    )


def test_answer_relevancy_range():
    score = answer_relevancy(
        "What is the Lambda timeout?",
        "The Lambda timeout limit is 15 minutes.",
    )
    assert 0.0 <= score <= 1.0
    assert score > 0.2
