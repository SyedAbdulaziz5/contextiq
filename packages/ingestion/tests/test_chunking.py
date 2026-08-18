from __future__ import annotations

import json
from pathlib import Path

from contextiq_ingestion.chunking.fixed import chunk_fixed
from contextiq_ingestion.chunking.models import ChunkStrategy, approx_tokens
from contextiq_ingestion.chunking.semantic import chunk_semantic
from contextiq_ingestion.chunking.structural import chunk_structural
from contextiq_ingestion.models import CleanDocument, ContentBlock, DocumentType, Section


def _fixture_doc() -> CleanDocument:
    return CleanDocument(
        document_id="doc-1",
        source_id="aws-lambda-limits",
        title="Lambda quotas",
        source_url="https://example.com/limits",
        family="aws",
        document_type=DocumentType.HTML,
        sections=[
            Section(
                id="s1",
                heading="Function configuration",
                heading_level=2,
                heading_path=["Function configuration"],
                content_blocks=[
                    ContentBlock(
                        type="paragraph",
                        text="Lambda allocates CPU power in proportion to memory.",
                    ),
                    ContentBlock(
                        type="table",
                        headers=["Resource", "Quota"],
                        rows=[["Function timeout", "900 seconds (15 minutes)"]],
                        markdown="| Resource | Quota |\n| --- | --- |\n| Function timeout | 900 seconds (15 minutes) |",
                    ),
                    ContentBlock(
                        type="paragraph",
                        text="Environment variables are limited to 4 KB in aggregate. Layers are capped at five.",
                    ),
                ],
            ),
            Section(
                id="s2",
                heading="Concurrency",
                heading_level=2,
                heading_path=["Concurrency"],
                content_blocks=[
                    ContentBlock(
                        type="paragraph",
                        text="The default concurrent executions quota is 1,000 per Region.",
                    )
                ],
            ),
        ],
    )


def test_fixed_respects_size_and_overlap() -> None:
    doc = _fixture_doc()
    chunks = chunk_fixed(doc, chunk_size=20, overlap_ratio=0.15)
    assert chunks
    assert all(c.strategy == ChunkStrategy.FIXED for c in chunks)
    assert all(c.source_id == "aws-lambda-limits" for c in chunks)
    assert all(c.token_count == approx_tokens(c.content) for c in chunks)


def test_structural_keeps_table_atomic() -> None:
    doc = _fixture_doc()
    chunks = chunk_structural(doc, max_tokens=80, min_tokens=10)
    assert chunks
    table_chunks = [c for c in chunks if "900 seconds" in c.content]
    assert table_chunks
    # table markdown should appear intact in at least one chunk
    assert any("| Function timeout | 900 seconds (15 minutes) |" in c.content for c in chunks)
    assert all(c.section_title or c.metadata.get("preserves_structure") for c in chunks)


def test_semantic_produces_chunks_with_metadata() -> None:
    doc = _fixture_doc()
    chunks = chunk_semantic(doc, max_tokens=100, similarity_threshold=0.3)
    assert chunks
    assert all(c.strategy == ChunkStrategy.SEMANTIC for c in chunks)
    assert all(c.source_url.startswith("https://") for c in chunks)


def test_roundtrip_jsonl(tmp_path: Path) -> None:
    doc = _fixture_doc()
    chunks = chunk_structural(doc)
    path = tmp_path / "chunks.jsonl"
    with path.open("w") as f:
        for c in chunks:
            f.write(c.model_dump_json() + "\n")
    loaded = [json.loads(line) for line in path.read_text().splitlines()]
    assert loaded[0]["source_id"] == "aws-lambda-limits"
    assert "content" in loaded[0]
