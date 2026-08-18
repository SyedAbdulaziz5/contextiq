from __future__ import annotations

from contextiq_ingestion.embeddings.cache import EmbeddedChunk
from contextiq_ingestion.embeddings.providers import LocalHashEmbedder
from contextiq_ingestion.query.hyde import TemplateHyDE
from contextiq_ingestion.query.pipeline import QueryPipeline
from contextiq_ingestion.query.rewriter import QueryRewriter, Turn
from contextiq_ingestion.query.router import QueryRouter, Route
from contextiq_ingestion.retrieval.hybrid import HybridRetriever


def test_router_greeting_and_rag() -> None:
    router = QueryRouter()
    assert router.route("Hi").route == Route.GREETING
    assert router.route("What can you do?").route == Route.META
    assert router.route("what is 2 + 2?").route == Route.CALCULATION
    assert router.route("what about the second one?").route == Route.CLARIFY
    assert router.route("What is the Lambda timeout?").route == Route.RAG


def test_rewriter_resolves_followup() -> None:
    rewriter = QueryRewriter()
    history = [Turn(role="user", content="Tell me about Next.js Server Components")]
    result = rewriter.rewrite("what about the second one?", history)
    assert result.changed
    assert "server component" in result.rewritten.lower()


def test_template_hyde_produces_answer_shaped_text() -> None:
    hyde = TemplateHyDE().generate("What is the Lambda timeout?")
    assert "timeout" in hyde.hypothetical_document.lower()
    assert len(hyde.hypothetical_document) > len(hyde.query)


def test_pipeline_skips_retrieval_on_greeting() -> None:
    emb = LocalHashEmbedder(dimensions=32)
    rows = [
        EmbeddedChunk(
            chunk_key="k1",
            document_id="00000000-0000-0000-0000-000000000001",
            source_id="aws-lambda-limits",
            strategy="structural",
            content="Function timeout is 900 seconds.",
            embedding=emb.embed_documents(["timeout"])[0],
            embedding_model="test",
            family="aws",
            source_url="https://example.com",
            title="limits",
        )
    ]
    pipeline = QueryPipeline(retriever=HybridRetriever(rows=rows, embedder=emb))
    result = pipeline.run("Hi")
    assert result.skipped_retrieval
    assert result.route.route == Route.GREETING
    assert result.hits == []


def test_pipeline_rewrites_then_retrieves() -> None:
    emb = LocalHashEmbedder(dimensions=32)
    rows = [
        EmbeddedChunk(
            chunk_key="k1",
            document_id="00000000-0000-0000-0000-000000000001",
            source_id="nextjs-server-and-client-components",
            strategy="structural",
            content="Next.js Server Components limitations and characteristics for rendering.",
            embedding=emb.embed_documents(["server components limitations"])[0],
            embedding_model="test",
            family="nextjs",
            source_url="https://example.com",
            title="components",
        )
    ]
    pipeline = QueryPipeline(retriever=HybridRetriever(rows=rows, embedder=emb))
    history = [Turn(role="user", content="Tell me about Next.js Server Components")]
    result = pipeline.run(
        "what about the second one?",
        history=history,
        force_rag=True,
        retrieval_mode="sparse",
        top_k=1,
    )
    assert not result.skipped_retrieval
    assert result.rewrite.changed
    assert "server component" in result.rewrite.rewritten.lower()
