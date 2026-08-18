from __future__ import annotations

from contextiq_ingestion.chunking.models import Chunk, ChunkStrategy, approx_tokens, make_chunk_id
from contextiq_ingestion.models import CleanDocument


def chunk_fixed(
    doc: CleanDocument,
    *,
    chunk_size: int = 500,
    overlap_ratio: float = 0.15,
) -> list[Chunk]:
    """
    Naive fixed-size chunking over flattened document text.

    Intentionally ignores structure — the baseline to beat.
    Overlap defaults to 15% of chunk_size (guide recommendation).
    """
    text = doc.content_text().strip()
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    overlap = max(0, int(chunk_size * overlap_ratio))
    step = max(1, chunk_size - overlap)
    chunks: list[Chunk] = []
    index = 0
    start = 0

    while start < len(words):
        end = min(len(words), start + chunk_size)
        window = words[start:end]
        content = " ".join(window).strip()
        if content:
            chunks.append(
                Chunk(
                    chunk_id=make_chunk_id(ChunkStrategy.FIXED.value, doc.source_id, index, content),
                    document_id=doc.document_id,
                    source_id=doc.source_id,
                    strategy=ChunkStrategy.FIXED,
                    content=content,
                    token_count=approx_tokens(content),
                    section_title=None,
                    section_id=None,
                    heading_path=[],
                    page_number=None,
                    document_type=doc.document_type.value,
                    family=doc.family,
                    source_url=doc.source_url,
                    title=doc.title,
                    metadata={
                        "chunk_size_target": chunk_size,
                        "overlap_tokens": overlap,
                        "word_start": start,
                        "word_end": end,
                        "preserves_structure": False,
                    },
                )
            )
            index += 1
        if end >= len(words):
            break
        start += step

    return chunks
