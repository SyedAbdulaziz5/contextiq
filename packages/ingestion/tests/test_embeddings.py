from __future__ import annotations

from contextiq_ingestion.chunking.models import Chunk, ChunkStrategy
from contextiq_ingestion.embeddings.cache import MemoryVectorIndex, EmbeddedChunk
from contextiq_ingestion.embeddings.mathutil import cosine_similarity, hashing_embed, l2_normalize
from contextiq_ingestion.embeddings.providers import LocalHashEmbedder
from contextiq_ingestion.embeddings.pipeline import chunk_to_embedded, embed_chunks


def test_cosine_identical_is_one() -> None:
    v = l2_normalize([1.0, 2.0, 3.0, 4.0])
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_orthogonalish() -> None:
    a = l2_normalize([1.0, 0.0, 0.0])
    b = l2_normalize([0.0, 1.0, 0.0])
    assert abs(cosine_similarity(a, b)) < 1e-9


def test_hashing_embed_is_deterministic_and_1024d() -> None:
    a = hashing_embed("Lambda timeout is 900 seconds", dimensions=1024)
    b = hashing_embed("Lambda timeout is 900 seconds", dimensions=1024)
    assert len(a) == 1024
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_local_embedder_and_memory_search_ranks_relevant_chunk() -> None:
    embedder = LocalHashEmbedder(dimensions=1024)
    chunks = [
        Chunk(
            chunk_id="structural:aws-lambda-limits:0001:aaaa",
            document_id="11111111-1111-1111-1111-111111111111",
            source_id="aws-lambda-limits",
            strategy=ChunkStrategy.STRUCTURAL,
            content="Function timeout is 900 seconds (15 minutes). This limit cannot be increased.",
            document_type="html",
            family="aws",
            source_url="https://example.com/limits",
            title="Lambda quotas",
            section_title="Function configuration",
        ),
        Chunk(
            chunk_id="structural:nextjs-fonts:0001:bbbb",
            document_id="22222222-2222-2222-2222-222222222222",
            source_id="nextjs-fonts",
            strategy=ChunkStrategy.STRUCTURAL,
            content="Use next/font to optimize and load Google Fonts automatically.",
            document_type="mdx",
            family="nextjs",
            source_url="https://example.com/fonts",
            title="Fonts",
            section_title="Fonts",
        ),
    ]
    rows = embed_chunks(chunks, embedder)
    index = MemoryVectorIndex(rows)
    q = embedder.embed_query("What is the maximum Lambda execution timeout?")
    hits = index.search(q, top_k=2)
    assert hits[0].chunk.source_id == "aws-lambda-limits"
    assert hits[0].score > hits[1].score


def test_chunk_to_embedded_preserves_metadata() -> None:
    chunk = Chunk(
        chunk_id="structural:x:0000:cccc",
        document_id="33333333-3333-3333-3333-333333333333",
        source_id="x",
        strategy=ChunkStrategy.STRUCTURAL,
        content="hello",
        document_type="html",
        family="aws",
        source_url="https://example.com",
        title="T",
        section_title="S",
        metadata={"preserves_structure": True},
    )
    row = chunk_to_embedded(chunk, [0.1] * 8, "local")
    assert isinstance(row, EmbeddedChunk)
    assert row.section_title == "S"
    assert row.metadata["preserves_structure"] is True
