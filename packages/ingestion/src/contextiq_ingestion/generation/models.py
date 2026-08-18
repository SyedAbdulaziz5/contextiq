from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from contextiq_ingestion.retrieval.types import RankedHit


class Citation(BaseModel):
    claim_span: str
    source_id: str  # S1, S2, ...
    chunk_key: str | None = None
    doc_source_id: str | None = None
    title: str | None = None
    section_title: str | None = None
    source_url: str | None = None
    snippet: str | None = None


class SourceRef(BaseModel):
    source_id: str  # S1
    chunk_key: str
    doc_source_id: str
    title: str | None = None
    section_title: str | None = None
    source_url: str | None = None
    family: str | None = None
    score: float | None = None
    snippet: str
    channels: list[str] = Field(default_factory=list)
    similarity: float | None = None  # dense cosine when available
    rerank_score: float | None = None
    sparse_score: float | None = None
    rrf_score: float | None = None


Confidence = Literal["high", "medium", "low", "none"]


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: Confidence = "medium"
    insufficient_context: bool = False
    sources: list[SourceRef] = Field(default_factory=list)
    display_answer: str | None = None  # answer with [n] chips for UI
    meta: dict[str, Any] = Field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "display_answer": self.display_answer or self.answer,
            "citations": [c.model_dump() for c in self.citations],
            "confidence": self.confidence,
            "insufficient_context": self.insufficient_context,
            "sources": [s.model_dump() for s in self.sources],
            "meta": self.meta,
            "grounded": not self.insufficient_context and bool(self.citations or self.sources),
        }


def hits_to_source_refs(hits: list[RankedHit]) -> list[SourceRef]:
    refs: list[SourceRef] = []
    for i, hit in enumerate(hits, start=1):
        sid = f"S{i}"
        md = hit.metadata or {}
        refs.append(
            SourceRef(
                source_id=sid,
                chunk_key=hit.chunk_key,
                doc_source_id=hit.source_id,
                title=hit.title,
                section_title=hit.section_title,
                source_url=hit.source_url,
                family=hit.family,
                score=hit.score,
                snippet=hit.content[:500],
                channels=list(hit.channels),
                similarity=_f(md.get("similarity") or md.get("dense_score")),
                rerank_score=_f(md.get("rerank_score")),
                sparse_score=_f(md.get("sparse_score")),
                rrf_score=_f(md.get("rrf_score")),
            )
        )
    return refs


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def assemble_context_block(refs: list[SourceRef]) -> str:
    parts: list[str] = []
    for ref in refs:
        header = f"[{ref.source_id}] title={ref.title or ''} section={ref.section_title or ''} url={ref.source_url or ''}"
        parts.append(f"{header}\n{ref.snippet}")
    return "\n\n".join(parts)


def answer_with_numeric_chips(answer: str, citations: list[Citation]) -> str:
    """Convert [S1] markers to [1] for compact UI chips."""
    text = answer
    for c in citations:
        num = c.source_id.lstrip("S")
        text = text.replace(f"[{c.source_id}]", f"[{num}]")
        text = text.replace(f"[{c.source_id.lower()}]", f"[{num}]")
    # also map bare S ids if model used them
    import re

    def repl(m: re.Match[str]) -> str:
        return f"[{m.group(1)}]"

    text = re.sub(r"\[S(\d+)\]", repl, text, flags=re.I)
    return text
