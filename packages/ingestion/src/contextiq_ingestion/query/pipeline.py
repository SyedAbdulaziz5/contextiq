from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from contextiq_ingestion.embeddings.cache import EmbeddedChunk
from contextiq_ingestion.query.hyde import HyDEGenerator, HyDEResult, get_hyde_generator
from contextiq_ingestion.query.rewriter import QueryRewriter, RewriteResult, Turn
from contextiq_ingestion.query.router import QueryRouter, Route, RouteDecision
from contextiq_ingestion.retrieval.hybrid import HybridRetriever, Mode, build_retriever
from contextiq_ingestion.retrieval.types import RankedHit

DenseStrategy = Literal["raw", "hyde"]


@dataclass
class QueryUnderstandingResult:
    original_query: str
    route: RouteDecision
    rewrite: RewriteResult
    hyde: HyDEResult | None
    dense_strategy: DenseStrategy
    retrieval_query_sparse: str | None
    retrieval_query_dense: str | None
    hits: list[RankedHit] = field(default_factory=list)
    skipped_retrieval: bool = False
    stage_ms: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_query": self.original_query,
            "route": {
                "route": self.route.route.value,
                "confidence": self.route.confidence,
                "reason": self.route.reason,
                "reply": self.route.reply,
            },
            "rewrite": {
                "original": self.rewrite.original,
                "rewritten": self.rewrite.rewritten,
                "changed": self.rewrite.changed,
                "reason": self.rewrite.reason,
                "history_used": self.rewrite.history_used,
            },
            "hyde": None
            if not self.hyde
            else {
                "method": self.hyde.method,
                "hypothetical_document": self.hyde.hypothetical_document,
            },
            "dense_strategy": self.dense_strategy,
            "retrieval_query_sparse": self.retrieval_query_sparse,
            "retrieval_query_dense": self.retrieval_query_dense,
            "skipped_retrieval": self.skipped_retrieval,
            "stage_ms": self.stage_ms,
            "hits": [
                {
                    "rank": h.rank,
                    "score": round(h.score, 4),
                    "source_id": h.source_id,
                    "section_title": h.section_title,
                    "channels": h.channels,
                    "preview": h.preview(),
                }
                for h in self.hits
            ],
        }


@dataclass
class QueryPipeline:
    retriever: HybridRetriever
    router: QueryRouter = field(default_factory=QueryRouter)
    rewriter: QueryRewriter = field(default_factory=QueryRewriter)
    hyde: HyDEGenerator = field(default_factory=get_hyde_generator)

    def run(
        self,
        query: str,
        *,
        history: list[Turn] | None = None,
        dense_strategy: DenseStrategy = "raw",
        retrieval_mode: Mode = "hybrid_rerank",
        family: str | None = None,
        top_k: int = 8,
        force_rag: bool = False,
    ) -> QueryUnderstandingResult:
        history = history or []
        stage_ms: dict[str, float] = {}

        t0 = time.perf_counter()
        route = self.router.route(query, has_history=bool(history))
        stage_ms["route"] = round((time.perf_counter() - t0) * 1000, 2)

        t0 = time.perf_counter()
        rewrite = self.rewriter.rewrite(query, history)
        stage_ms["rewrite"] = round((time.perf_counter() - t0) * 1000, 2)

        if route.route != Route.RAG and not force_rag:
            return QueryUnderstandingResult(
                original_query=query,
                route=route,
                rewrite=rewrite,
                hyde=None,
                dense_strategy=dense_strategy,
                retrieval_query_sparse=None,
                retrieval_query_dense=None,
                hits=[],
                skipped_retrieval=True,
                stage_ms=stage_ms,
            )

        sparse_q = rewrite.rewritten
        hyde_result: HyDEResult | None = None
        if dense_strategy == "hyde":
            t0 = time.perf_counter()
            hyde_result = self.hyde.generate(sparse_q)
            stage_ms["hyde"] = round((time.perf_counter() - t0) * 1000, 2)
            dense_q = hyde_result.hypothetical_document
        else:
            dense_q = sparse_q

        t0 = time.perf_counter()
        hits = self.retriever.retrieve(
            sparse_q,
            mode=retrieval_mode,
            family=family,
            top_k=top_k,
            dense_query=dense_q,
            sparse_query=sparse_q,
        )
        stage_ms["retrieve_total"] = round((time.perf_counter() - t0) * 1000, 2)
        for k, v in (self.retriever.last_timings_ms or {}).items():
            stage_ms[k] = v

        return QueryUnderstandingResult(
            original_query=query,
            route=route,
            rewrite=rewrite,
            hyde=hyde_result,
            dense_strategy=dense_strategy,
            retrieval_query_sparse=sparse_q,
            retrieval_query_dense=dense_q,
            hits=hits,
            skipped_retrieval=False,
            stage_ms=stage_ms,
        )


def build_query_pipeline(
    rows: list[EmbeddedChunk],
    *,
    provider: str | None = None,
    hyde_provider: str | None = None,
) -> QueryPipeline:
    return QueryPipeline(
        retriever=build_retriever(rows, provider=provider),
        hyde=get_hyde_generator(hyde_provider),
    )
