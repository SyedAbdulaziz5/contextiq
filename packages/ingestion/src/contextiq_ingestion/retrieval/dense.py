from __future__ import annotations

from contextiq_ingestion.embeddings.cache import EmbeddedChunk, MemoryVectorIndex
from contextiq_ingestion.embeddings.providers import Embedder
from contextiq_ingestion.retrieval.types import RankedHit


class DenseRetriever:
    """Cosine dense retrieval over an in-memory embedding index (or precomputed vectors)."""

    def __init__(self, rows: list[EmbeddedChunk], embedder: Embedder) -> None:
        self.rows = rows
        self.embedder = embedder
        self.index = MemoryVectorIndex(rows)
        self.by_key = {r.chunk_key: r for r in rows}

    def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        family: str | None = None,
    ) -> list[RankedHit]:
        qvec = self.embedder.embed_query(query)
        hits = self.index.search(qvec, top_k=top_k, family=family)
        out: list[RankedHit] = []
        for h in hits:
            out.append(
                RankedHit(
                    chunk_key=h.chunk.chunk_key,
                    source_id=h.chunk.source_id,
                    content=h.chunk.content,
                    score=h.score,
                    rank=h.rank,
                    section_title=h.chunk.section_title,
                    family=h.chunk.family,
                    source_url=h.chunk.source_url,
                    title=h.chunk.title,
                    channels=["dense"],
                )
            )
        return out
