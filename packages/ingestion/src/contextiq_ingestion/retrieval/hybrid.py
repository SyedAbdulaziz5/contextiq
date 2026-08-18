from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from contextiq_ingestion.embeddings.cache import EmbeddedChunk
from contextiq_ingestion.embeddings.providers import Embedder, get_embedder
from contextiq_ingestion.retrieval.dense import DenseRetriever
from contextiq_ingestion.retrieval.rerank import FeatureReranker
from contextiq_ingestion.retrieval.rrf import reciprocal_rank_fusion
from contextiq_ingestion.retrieval.sparse import SparseBM25Retriever
from contextiq_ingestion.retrieval.types import RankedHit

Mode = Literal["dense", "sparse", "hybrid", "hybrid_rerank"]


@dataclass
class HybridRetriever:
    """
    Dense + sparse → RRF → optional feature rerank.

    Defaults match the guide: fetch ~20 from each channel, fuse to ~30, rerank to 5–8.
    """

    rows: list[EmbeddedChunk]
    embedder: Embedder
    rrf_k: int = 60
    dense_k: int = 20
    sparse_k: int = 20
    fuse_k: int = 30
    final_k: int = 8
    last_timings_ms: dict[str, float] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.dense = DenseRetriever(self.rows, self.embedder)
        self.sparse = SparseBM25Retriever(self.rows)  # type: ignore[arg-type]
        self.reranker = FeatureReranker()
        self.by_key = {r.chunk_key: r for r in self.rows}
        self.last_timings_ms = {}

    def _hit_from_key(
        self,
        key: str,
        score: float,
        rank: int,
        channels: list[str],
        *,
        metadata: dict | None = None,
    ) -> RankedHit:
        row = self.by_key[key]
        return RankedHit(
            chunk_key=row.chunk_key,
            source_id=row.source_id,
            content=row.content,
            score=score,
            rank=rank,
            section_title=row.section_title,
            family=row.family,
            source_url=row.source_url,
            title=row.title,
            channels=channels,
            metadata=dict(metadata or {}),
        )

    def retrieve(
        self,
        query: str,
        *,
        mode: Mode = "hybrid_rerank",
        family: str | None = None,
        top_k: int | None = None,
        dense_query: str | None = None,
        sparse_query: str | None = None,
    ) -> list[RankedHit]:
        """
        query: used for reranking and as default for both channels
        dense_query: optional override (e.g. HyDE hypothetical document)
        sparse_query: optional override (e.g. rewritten standalone question)
        """
        final_k = top_k or self.final_k
        d_q = dense_query if dense_query is not None else query
        s_q = sparse_query if sparse_query is not None else query
        timings: dict[str, float] = {}

        if mode == "dense":
            t0 = time.perf_counter()
            hits = self.dense.search(d_q, top_k=final_k, family=family)
            timings["dense"] = round((time.perf_counter() - t0) * 1000, 2)
            self.last_timings_ms = timings
            return hits

        if mode == "sparse":
            t0 = time.perf_counter()
            hits = self.sparse.search(s_q, top_k=final_k, family=family)
            timings["sparse"] = round((time.perf_counter() - t0) * 1000, 2)
            self.last_timings_ms = timings
            return hits

        t0 = time.perf_counter()
        dense_hits = self.dense.search(d_q, top_k=self.dense_k, family=family)
        timings["dense"] = round((time.perf_counter() - t0) * 1000, 2)

        t0 = time.perf_counter()
        sparse_hits = self.sparse.search(s_q, top_k=self.sparse_k, family=family)
        timings["sparse"] = round((time.perf_counter() - t0) * 1000, 2)

        channel_map: dict[str, set[str]] = {}
        dense_scores: dict[str, float] = {}
        sparse_scores: dict[str, float] = {}
        for h in dense_hits:
            channel_map.setdefault(h.chunk_key, set()).add("dense")
            dense_scores[h.chunk_key] = h.score
        for h in sparse_hits:
            channel_map.setdefault(h.chunk_key, set()).add("sparse")
            sparse_scores[h.chunk_key] = h.score

        # Hashing dense is weak — don't let it dominate RRF.
        # Real SBERT / Bedrock dense gets equal weight with sparse.
        dense_weight = 0.35 if self.embedder.name.startswith("local-hashing") else 1.0
        sparse_weight = 1.0

        t0 = time.perf_counter()
        fused = reciprocal_rank_fusion(
            [
                [h.chunk_key for h in dense_hits],
                [h.chunk_key for h in sparse_hits],
            ],
            k=self.rrf_k,
            weights=[dense_weight, sparse_weight],
        )[: self.fuse_k]
        timings["rrf"] = round((time.perf_counter() - t0) * 1000, 2)

        fused_hits: list[RankedHit] = []
        for rank, (key, score) in enumerate(fused, start=1):
            if key not in self.by_key:
                continue
            channels = sorted(channel_map.get(key, set()) | {"rrf"})
            fused_hits.append(
                self._hit_from_key(
                    key,
                    score,
                    rank,
                    channels,
                    metadata={
                        "dense_score": dense_scores.get(key),
                        "sparse_score": sparse_scores.get(key),
                        "rrf_score": score,
                        "similarity": dense_scores.get(key),
                    },
                )
            )

        if mode == "hybrid":
            self.last_timings_ms = timings
            return fused_hits[:final_k]

        # hybrid_rerank — rerank against the human/sparse query, not the HyDE blob
        t0 = time.perf_counter()
        out = self.reranker.rerank(s_q, fused_hits, top_k=final_k)
        timings["rerank"] = round((time.perf_counter() - t0) * 1000, 2)
        self.last_timings_ms = timings
        return out


def build_retriever(
    rows: list[EmbeddedChunk],
    *,
    provider: str | None = None,
) -> HybridRetriever:
    return HybridRetriever(rows=rows, embedder=get_embedder(provider))
