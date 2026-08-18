from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Iterator, Literal

from contextiq_ingestion.embeddings.cache import cache_path, load_embedding_cache
from contextiq_ingestion.generation.bedrock_gen import BedrockGroundedGenerator
from contextiq_ingestion.generation.local import LocalGroundedGenerator
from contextiq_ingestion.generation.models import GroundedAnswer
from contextiq_ingestion.generation.ollama_gen import OllamaGroundedGenerator
from contextiq_ingestion.generation.prompts import REFUSAL_TEXT
from contextiq_ingestion.observability.trace import (
    QueryTrace,
    StageTiming,
    Timer,
    estimate_cost_detail,
    estimate_tokens,
    get_trace_store,
    new_trace_id,
)
from contextiq_ingestion.query.pipeline import QueryPipeline, build_query_pipeline
from contextiq_ingestion.query.rewriter import Turn

GeneratorName = Literal["ollama", "extractive", "local", "bedrock"]


def get_generator(provider: str | None = None):
    """
    Defaults to Ollama when the daemon is up; otherwise extractive (always free).

    Providers: ollama | extractive | local | bedrock
    """
    choice = (provider or os.getenv("CONTEXTIQ_GENERATOR") or "ollama").lower()
    if choice in {"extractive", "local-extractive"}:
        return LocalGroundedGenerator()
    if choice in {"ollama", "local"}:
        gen = OllamaGroundedGenerator()
        # Soft fallback when daemon is down or model not pulled yet
        if not gen.available():
            return LocalGroundedGenerator()
        return gen
    if choice in {"bedrock", "claude"}:
        return BedrockGroundedGenerator()
    raise ValueError(f"Unknown generator: {choice} (use ollama|extractive|bedrock)")


@dataclass
class ChatResult:
    query: str
    route: str
    rewrite: str | None
    answer: GroundedAnswer
    retrieval_skipped: bool
    trace_id: str | None = None
    trace: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "route": self.route,
            "rewrite": self.rewrite,
            "retrieval_skipped": self.retrieval_skipped,
            "trace_id": self.trace_id,
            "trace": self.trace,
            **self.answer.to_public_dict(),
        }


@dataclass
class GroundedChatPipeline:
    query_pipeline: QueryPipeline
    generator: Any

    def ask(
        self,
        query: str,
        *,
        history: list[Turn] | None = None,
        family: str | None = None,
        top_k: int = 6,
        retrieval_mode: str = "hybrid_rerank",
        force_rag: bool = False,
        record_trace: bool = True,
    ) -> ChatResult:
        trace_id = new_trace_id()
        t_total = Timer()
        stages: list[StageTiming] = []

        understood = self.query_pipeline.run(
            query,
            history=history,
            dense_strategy="raw",
            retrieval_mode=retrieval_mode,  # type: ignore[arg-type]
            family=family,
            top_k=top_k,
            force_rag=force_rag,
        )
        # Prefer fine-grained timers from the query/retrieve path
        stage_order = (
            "route",
            "rewrite",
            "hyde",
            "dense",
            "sparse",
            "rrf",
            "rerank",
            "retrieve_total",
        )
        for name in stage_order:
            if name in understood.stage_ms and name != "retrieve_total":
                stages.append(StageTiming(name, float(understood.stage_ms[name])))
        # If fine timings missing (tests/mocks), fall back to aggregate
        if not stages and understood.stage_ms.get("retrieve_total") is not None:
            stages.append(
                StageTiming("retrieve_total", float(understood.stage_ms["retrieve_total"]))
            )

        # Non-RAG routes: return router reply as grounded-looking payload
        if understood.skipped_retrieval:
            reply = understood.route.reply or REFUSAL_TEXT
            answer = GroundedAnswer(
                answer=reply,
                citations=[],
                confidence="high",
                insufficient_context=False,
                sources=[],
                display_answer=reply,
                meta={
                    "generator": "router",
                    "route": understood.route.route.value,
                },
            )
            result = ChatResult(
                query=query,
                route=understood.route.route.value,
                rewrite=understood.rewrite.rewritten,
                answer=answer,
                retrieval_skipped=True,
                trace_id=trace_id,
            )
            if record_trace:
                result.trace = self._persist_trace(
                    trace_id=trace_id,
                    query=query,
                    result=result,
                    stages=stages,
                    total_ms=t_total.ms(),
                    hits=[],
                )
            return result

        t = Timer()
        question_for_gen = understood.rewrite.rewritten
        grounded = self.generator.generate(question_for_gen, understood.hits)
        stages.append(StageTiming("generate", t.ms()))

        grounded.meta = {
            **grounded.meta,
            "route": understood.route.route.value,
            "rewrite": understood.rewrite.rewritten,
            "hit_count": len(understood.hits),
            "trace_id": trace_id,
        }
        result = ChatResult(
            query=query,
            route=understood.route.route.value,
            rewrite=understood.rewrite.rewritten,
            answer=grounded,
            retrieval_skipped=False,
            trace_id=trace_id,
        )
        if record_trace:
            result.trace = self._persist_trace(
                trace_id=trace_id,
                query=query,
                result=result,
                stages=stages,
                total_ms=t_total.ms(),
                hits=understood.hits,
            )
        return result

    def _persist_trace(
        self,
        *,
        trace_id: str,
        query: str,
        result: ChatResult,
        stages: list[StageTiming],
        total_ms: float,
        hits: list,
    ) -> dict[str, Any]:
        gen_name = str(result.answer.meta.get("generator") or "local")
        answer_text = result.answer.display_answer or result.answer.answer
        context_blob = "\n".join(getattr(h, "content", "")[:400] for h in hits)
        in_tok = estimate_tokens(query + "\n" + (result.rewrite or "") + "\n" + context_blob)
        out_tok = estimate_tokens(answer_text)
        scores = []
        for h in hits:
            md = getattr(h, "metadata", {}) or {}
            scores.append(
                {
                    "chunk_key": h.chunk_key,
                    "source_id": h.source_id,
                    "title": h.title,
                    "section_title": h.section_title,
                    "score": h.score,
                    "similarity": md.get("similarity") or md.get("dense_score"),
                    "rerank_score": md.get("rerank_score"),
                    "channels": list(h.channels),
                }
            )
        refused = bool(result.answer.insufficient_context)
        grounded = (not refused) and (bool(result.answer.citations) or bool(result.answer.sources))
        citations = []
        for c in result.answer.citations or []:
            citations.append(
                {
                    "source_id": c.source_id,
                    "claim_span": c.claim_span,
                    "doc_source_id": c.doc_source_id,
                    "chunk_key": c.chunk_key,
                    "title": c.title,
                    "section_title": c.section_title,
                }
            )
        cost = estimate_cost_detail(
            input_tokens=in_tok, output_tokens=out_tok, generator=gen_name
        )
        trace = QueryTrace(
            trace_id=trace_id,
            ts=time.time(),
            query=query,
            rewritten_query=result.rewrite,
            route=result.route,
            retrieval_skipped=result.retrieval_skipped,
            stages=stages,
            retrieved_chunk_ids=[h.chunk_key for h in hits],
            retrieval_scores=scores,
            citations=citations,
            answer_preview=answer_text[:280],
            confidence=result.answer.confidence,
            refused=refused,
            grounded=grounded,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=cost.usd,
            cost=cost.to_dict(),
            total_latency_ms=total_ms,
            generator=gen_name,
            meta={
                "hit_count": len(hits),
                "citation_count": len(citations),
                "stage_sum_ms": round(sum(s.latency_ms for s in stages), 2),
            },
        )
        get_trace_store().append(trace)
        return trace.to_dict()

    def ask_stream_events(
        self,
        query: str,
        *,
        history: list[Turn] | None = None,
        family: str | None = None,
        top_k: int = 6,
    ) -> Iterator[dict[str, Any]]:
        """Yield SSE-friendly event dicts: meta → sources → token* → final."""
        result = self.ask(query, history=history, family=family, top_k=top_k)
        yield {
            "event": "meta",
            "data": {
                "query": result.query,
                "route": result.route,
                "rewrite": result.rewrite,
                "retrieval_skipped": result.retrieval_skipped,
                "confidence": result.answer.confidence,
                "insufficient_context": result.answer.insufficient_context,
                "trace_id": result.trace_id,
                "grounded": not result.answer.insufficient_context
                and bool(result.answer.citations or result.answer.sources),
            },
        }
        yield {
            "event": "sources",
            "data": {"sources": [s.model_dump() for s in result.answer.sources]},
        }
        if result.trace:
            yield {"event": "trace", "data": result.trace}
        text = result.answer.display_answer or result.answer.answer
        buf = ""
        for word in text.split(" "):
            piece = word if not buf else " " + word
            buf += piece
            yield {"event": "token", "data": {"text": piece}}
        yield {
            "event": "final",
            "data": result.to_dict(),
        }


def build_chat_pipeline(
    *,
    strategy: str = "structural",
    embed_provider: str | None = None,
    generator: str | None = None,
) -> GroundedChatPipeline:
    rows = load_embedding_cache(cache_path(strategy))
    return GroundedChatPipeline(
        query_pipeline=build_query_pipeline(rows, provider=embed_provider),
        generator=get_generator(generator),
    )
