from __future__ import annotations

import math
import re
from collections import Counter

from contextiq_ingestion.chunking.models import (
    Chunk,
    ChunkStrategy,
    approx_tokens,
    make_chunk_id,
    split_sentences,
)
from contextiq_ingestion.chunking.structural import chunk_structural
from contextiq_ingestion.models import CleanDocument


_TOKEN = re.compile(r"[a-z0-9_./:+-]+", re.I)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text) if len(t) > 1]


def _tfidf_vectors(texts: list[str]) -> list[dict[str, float]]:
    docs = [_tokenize(t) for t in texts]
    df: Counter[str] = Counter()
    for toks in docs:
        df.update(set(toks))
    n = max(len(docs), 1)
    vectors: list[dict[str, float]] = []
    for toks in docs:
        tf = Counter(toks)
        length = len(toks) or 1
        vec: dict[str, float] = {}
        for term, count in tf.items():
            idf = math.log((1 + n) / (1 + df[term])) + 1.0
            vec[term] = (count / length) * idf
        vectors.append(vec)
    return vectors


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _retag_semantic(chunk: Chunk, index: int, reason: str) -> Chunk:
    data = chunk.model_dump()
    data["strategy"] = ChunkStrategy.SEMANTIC
    data["chunk_id"] = make_chunk_id(
        ChunkStrategy.SEMANTIC.value, chunk.source_id, index, chunk.content
    )
    meta = dict(data.get("metadata") or {})
    meta["semantic_fallback"] = reason
    meta["embedding"] = "tfidf_local"
    data["metadata"] = meta
    return Chunk(**data)


def _units_from_doc(doc: CleanDocument) -> list[tuple[str, dict]]:
    """Sentence/block units with section metadata; tables/code stay whole."""
    units: list[tuple[str, dict]] = []
    for section in doc.sections:
        heading = section.heading
        base = {
            "section_id": section.id,
            "section_title": heading,
            "heading_path": list(section.heading_path),
            "page_number": section.page_number,
        }
        emitted_heading = False
        for block in section.content_blocks:
            text = block.to_plaintext().strip()
            if not text:
                continue
            if block.type in {"table", "code"}:
                prefix = f"## {heading}\n\n" if heading and not emitted_heading else ""
                emitted_heading = True
                units.append(
                    (
                        f"{prefix}{text}".strip(),
                        {**base, "block_types": [block.type], "atomic": True},
                    )
                )
                continue
            sentences = split_sentences(text) or [text]
            for sentence in sentences:
                prefix = f"## {heading}\n\n" if heading and not emitted_heading else ""
                emitted_heading = True
                units.append(
                    (
                        f"{prefix}{sentence}".strip(),
                        {**base, "block_types": [block.type], "atomic": False},
                    )
                )
        if heading and not section.content_blocks:
            units.append((f"## {heading}", {**base, "block_types": ["heading"], "atomic": False}))

    if not units:
        text = doc.content_text().strip()
        for sentence in split_sentences(text) or ([text] if text else []):
            units.append(
                (
                    sentence,
                    {
                        "section_title": None,
                        "section_id": None,
                        "heading_path": [],
                        "block_types": ["paragraph"],
                        "atomic": False,
                    },
                )
            )
    return units


def chunk_semantic(
    doc: CleanDocument,
    *,
    max_tokens: int = 500,
    min_tokens: int = 80,
    similarity_threshold: float = 0.18,
) -> list[Chunk]:
    """
    Local semantic chunking (TF-IDF cosine boundaries):

    1. Split into sentences/blocks (tables/code atomic)
    2. Build per-document TF-IDF vectors
    3. New chunk when adjacent similarity < threshold AND current group
       already reached min_tokens, OR max_tokens would be exceeded

    Phase 3 can swap TF-IDF for Bedrock Titan embeddings for sharper boundaries.
    """
    units = _units_from_doc(doc)
    if len(units) <= 2:
        return [
            _retag_semantic(c, i, "too_few_units")
            for i, c in enumerate(chunk_structural(doc, max_tokens=max_tokens))
        ]

    texts = [u[0] for u in units]
    vectors = _tfidf_vectors(texts)

    groups: list[list[int]] = [[0]]
    for i in range(1, len(units)):
        sim = _cosine(vectors[i - 1], vectors[i])
        current_text = "\n\n".join(units[j][0] for j in groups[-1])
        current_tokens = approx_tokens(current_text)
        next_tokens = approx_tokens(units[i][0])
        would_exceed = current_tokens + next_tokens > max_tokens
        # Only allow topic-break splits once the current chunk is substantial
        topic_break = sim < similarity_threshold and current_tokens >= min_tokens
        if would_exceed or topic_break:
            groups.append([i])
        else:
            groups[-1].append(i)

    chunks: list[Chunk] = []
    for index, group in enumerate(groups):
        parts = [units[i][0] for i in group]
        content = "\n\n".join(parts).strip()
        if not content:
            continue
        first_meta = units[group[0]][1]
        block_types: set[str] = set()
        for i in group:
            block_types.update(units[i][1].get("block_types") or [])
        sims = [
            round(_cosine(vectors[a], vectors[b]), 4)
            for a, b in zip(group, group[1:])
        ]
        chunks.append(
            Chunk(
                chunk_id=make_chunk_id(ChunkStrategy.SEMANTIC.value, doc.source_id, index, content),
                document_id=doc.document_id,
                source_id=doc.source_id,
                strategy=ChunkStrategy.SEMANTIC,
                content=content,
                token_count=approx_tokens(content),
                section_title=first_meta.get("section_title"),
                section_id=first_meta.get("section_id"),
                heading_path=list(first_meta.get("heading_path") or []),
                page_number=first_meta.get("page_number"),
                document_type=doc.document_type.value,
                family=doc.family,
                source_url=doc.source_url,
                title=doc.title,
                metadata={
                    "max_tokens": max_tokens,
                    "min_tokens": min_tokens,
                    "similarity_threshold": similarity_threshold,
                    "boundary_similarities": sims,
                    "unit_count": len(group),
                    "block_types": sorted(block_types),
                    "embedding": "tfidf_local",
                    "preserves_structure": True,
                },
            )
        )

    if not chunks:
        return [
            _retag_semantic(c, i, "empty_semantic")
            for i, c in enumerate(chunk_structural(doc, max_tokens=max_tokens))
        ]
    return chunks
