from __future__ import annotations

from contextiq_ingestion.embeddings.cache import EmbeddedChunk
from contextiq_ingestion.embeddings.providers import LocalHashEmbedder
from contextiq_ingestion.retrieval.hybrid import HybridRetriever
from contextiq_ingestion.retrieval.rrf import reciprocal_rank_fusion


def _row(key: str, source: str, content: str, family: str = "aws") -> EmbeddedChunk:
    emb = LocalHashEmbedder(dimensions=64).embed_documents([content])[0]
    return EmbeddedChunk(
        chunk_key=key,
        document_id="00000000-0000-0000-0000-000000000001",
        source_id=source,
        strategy="structural",
        content=content,
        embedding=emb,
        embedding_model="test",
        section_title="S",
        family=family,
        source_url="https://example.com",
        title=source,
    )


def test_rrf_prefers_docs_in_both_lists() -> None:
    fused = reciprocal_rank_fusion(
        [
            ["a", "b", "c"],
            ["c", "a", "d"],
        ],
        k=60,
    )
    # a and c appear in both → should beat b and d
    order = [doc for doc, _ in fused]
    assert order[0] in {"a", "c"}
    assert set(order[:2]) == {"a", "c"}


def test_hybrid_exact_id_prefers_sparse_signal() -> None:
    rows = [
        _row(
            "k1",
            "aws-bedrock-titan-embeddings",
            "Model ID amazon.titan-embed-text-v2:0 outputs 1024 dimensions by default.",
        ),
        _row(
            "k2",
            "nextjs-fonts",
            "Optimize fonts with next/font for better loading performance in apps.",
            family="nextjs",
        ),
        _row(
            "k3",
            "aws-lambda-memory",
            "Memory settings control CPU allocation for functions in a Region.",
        ),
    ]
    retriever = HybridRetriever(rows=rows, embedder=LocalHashEmbedder(dimensions=64), final_k=3)
    q = "What is amazon.titan-embed-text-v2:0?"
    sparse = retriever.retrieve(q, mode="sparse", top_k=3)
    assert sparse[0].source_id == "aws-bedrock-titan-embeddings"
    hybrid = retriever.retrieve(q, mode="hybrid_rerank", top_k=3)
    assert hybrid[0].source_id == "aws-bedrock-titan-embeddings"
    assert "rerank" in hybrid[0].channels or "rrf" in hybrid[0].channels or "sparse" in hybrid[0].channels


def test_feature_reranker_boosts_error_code() -> None:
    rows = [
        _row("a", "aws-lambda-scaling", "Additional requests fail with a throttling error (429 status code)."),
        _row("b", "aws-lambda-layers", "A Lambda layer is a zip file archive with dependencies."),
    ]
    retriever = HybridRetriever(rows=rows, embedder=LocalHashEmbedder(dimensions=64), final_k=2)
    hits = retriever.retrieve("HTTP status code 429 throttling", mode="hybrid_rerank", top_k=2)
    assert hits[0].source_id == "aws-lambda-scaling"
