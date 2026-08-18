"""Phase 7 — RAG evaluation metrics (implemented, not RAGAS-wrapped)."""

from __future__ import annotations

import re
from typing import Sequence

from contextiq_ingestion.embeddings.mathutil import cosine_similarity, tokenize
from contextiq_ingestion.embeddings.providers import LocalHashEmbedder
from contextiq_ingestion.retrieval.types import RankedHit

_STOP = {
    "what",
    "when",
    "where",
    "which",
    "who",
    "how",
    "does",
    "do",
    "did",
    "the",
    "and",
    "for",
    "are",
    "is",
    "was",
    "with",
    "from",
    "this",
    "that",
    "your",
    "about",
    "into",
    "have",
    "has",
    "can",
    "will",
    "would",
    "could",
    "should",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "or",
    "as",
    "by",
    "it",
    "be",
}


def content_terms(text: str) -> set[str]:
    return {t.rstrip(".:") for t in tokenize(text) if len(t) > 2 and t.lower() not in _STOP}


def context_precision(hits: Sequence[RankedHit], expected_source_ids: list[str]) -> float:
    """Of retrieved chunks, what fraction belong to an expected source doc."""
    if not hits:
        return 0.0
    expected = set(expected_source_ids)
    if not expected:
        return 0.0
    return sum(1 for h in hits if h.source_id in expected) / len(hits)


def context_recall(hits: Sequence[RankedHit], expected_source_ids: list[str]) -> float:
    """Of expected source docs, what fraction appear in the retrieved set."""
    expected = set(expected_source_ids)
    if not expected:
        return 0.0
    retrieved = {h.source_id for h in hits}
    return len(expected & retrieved) / len(expected)


def split_claims(answer: str) -> list[str]:
    """Split an answer into claim-like units (sentences / table facts)."""
    text = (answer or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    claims: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) < 12:
            continue
        # Drop citation chips for claim text
        clean = re.sub(r"\[\d+\]|\[S\d+\]", "", p, flags=re.I).strip()
        if len(clean) >= 12:
            claims.append(clean)
    return claims


def claim_supported(claim: str, context: str, *, min_overlap: float = 0.35) -> bool:
    """
    Heuristic faithfulness check: a claim is supported if enough of its
    content terms appear in the retrieved context (or it's a refusal).
    """
    c_terms = content_terms(claim)
    if not c_terms:
        return True
    ctx = content_terms(context)
    if not ctx:
        return False
    hit = sum(1 for t in c_terms if t in ctx)
    return (hit / len(c_terms)) >= min_overlap


def faithfulness(answer: str, context_chunks: Sequence[str], *, refused: bool = False) -> float:
    """
    Fraction of answer claims supported by retrieved context.
    Refusals are vacuously faithful (no invented facts).
    """
    if refused:
        return 1.0
    claims = split_claims(answer)
    if not claims:
        return 1.0 if not (answer or "").strip() else 0.0
    context = "\n".join(context_chunks)
    supported = sum(1 for c in claims if claim_supported(c, context))
    return supported / len(claims)


def answer_relevancy(question: str, answer: str, *, refused: bool = False) -> float:
    """
    How well the answer addresses the question.
    Uses local hashing-embedding cosine (same plumbing as Phase 3).
    Refusals score mid-high only when they clearly refuse (not random text).
    """
    if not answer.strip():
        return 0.0
    if refused:
        # A clear refusal is relevant to an out-of-scope ask; still not a topical answer.
        return 0.85
    embedder = LocalHashEmbedder(dimensions=256)
    q_vec = embedder.embed_query(question)
    a_vec = embedder.embed_query(answer)
    cos = cosine_similarity(q_vec, a_vec)
    # Map typical [-0.1, 0.6] hashing cosines into [0, 1] softly
    score = max(0.0, min(1.0, (cos + 0.05) / 0.55))
    # Blend with lexical overlap so exact fact answers aren't punished by hashing noise
    q_terms = content_terms(question)
    a_terms = content_terms(answer)
    if q_terms:
        lex = len(q_terms & a_terms) / len(q_terms)
        score = 0.45 * score + 0.55 * lex
    return float(score)


def hallucination_rate(answer: str, context_chunks: Sequence[str], *, refused: bool = False) -> float:
    """1 - faithfulness (share of unsupported claims)."""
    return 1.0 - faithfulness(answer, context_chunks, refused=refused)
