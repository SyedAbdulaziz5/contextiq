from __future__ import annotations

from contextiq_ingestion.chunking.models import (
    Chunk,
    ChunkStrategy,
    approx_tokens,
    make_chunk_id,
    split_sentences,
)
from contextiq_ingestion.models import CleanDocument, ContentBlock, Section


def _block_text(block: ContentBlock) -> str:
    return block.to_plaintext().strip()


def _pack_units(
    units: list[tuple[str, dict]],
    *,
    max_tokens: int,
) -> list[tuple[str, dict]]:
    """Greedy pack units into groups under max_tokens; never split a unit marked atomic."""
    packed: list[tuple[str, dict]] = []
    buf_parts: list[str] = []
    buf_meta: dict | None = None
    buf_tokens = 0

    def flush() -> None:
        nonlocal buf_parts, buf_meta, buf_tokens
        if buf_parts:
            packed.append(("\n\n".join(buf_parts).strip(), dict(buf_meta or {})))
        buf_parts, buf_meta, buf_tokens = [], None, 0

    for text, meta in units:
        tokens = approx_tokens(text)
        atomic = bool(meta.get("atomic"))

        if tokens > max_tokens and not atomic:
            flush()
            # sentence-split oversized non-atomic units
            for sentence in split_sentences(text) or [text]:
                st = approx_tokens(sentence)
                if buf_tokens + st > max_tokens and buf_parts:
                    flush()
                if not buf_parts:
                    buf_meta = {**meta, "split_from_oversized": True}
                buf_parts.append(sentence)
                buf_tokens += st
                if buf_tokens >= max_tokens:
                    flush()
            continue

        if tokens > max_tokens and atomic:
            # Keep atomic table/code intact even if over budget (document the overflow)
            flush()
            packed.append((text, {**meta, "over_budget": True}))
            continue

        if buf_tokens + tokens > max_tokens and buf_parts:
            flush()

        if not buf_parts:
            buf_meta = dict(meta)
        else:
            # merge metadata conservatively
            assert buf_meta is not None
            if meta.get("section_id") and buf_meta.get("section_id") != meta.get("section_id"):
                buf_meta["merged_sections"] = True
            types = set(buf_meta.get("block_types", [])) | set(meta.get("block_types", []))
            buf_meta["block_types"] = sorted(types)

        buf_parts.append(text)
        buf_tokens += tokens

    flush()
    return [(t, m) for t, m in packed if t]


def _section_units(section: Section, doc: CleanDocument) -> list[tuple[str, dict]]:
    units: list[tuple[str, dict]] = []
    heading_prefix = ""
    if section.heading:
        level = section.heading_level or 2
        heading_prefix = "#" * max(1, min(level, 6)) + f" {section.heading}"

    base_meta = {
        "section_id": section.id,
        "section_title": section.heading,
        "heading_path": list(section.heading_path),
        "page_number": section.page_number,
    }

    if not section.content_blocks:
        if heading_prefix:
            units.append(
                (
                    heading_prefix,
                    {**base_meta, "block_types": ["heading"], "atomic": False},
                )
            )
        return units

    # First unit includes heading + first block when possible
    pending_heading = heading_prefix
    for block in section.content_blocks:
        text = _block_text(block)
        if not text:
            continue
        atomic = block.type in {"table", "code"}
        content = f"{pending_heading}\n\n{text}".strip() if pending_heading else text
        pending_heading = ""
        units.append(
            (
                content,
                {
                    **base_meta,
                    "block_types": [block.type],
                    "atomic": atomic,
                },
            )
        )
    if pending_heading:
        units.append((pending_heading, {**base_meta, "block_types": ["heading"], "atomic": False}))
    return units


def chunk_structural(
    doc: CleanDocument,
    *,
    max_tokens: int = 500,
    min_tokens: int = 50,
) -> list[Chunk]:
    """
    Structure-aware chunking:
    headings → blocks → sentences.
    Tables and code fences stay atomic when possible.
    Small adjacent pieces merge up toward max_tokens.
    """
    units: list[tuple[str, dict]] = []
    for section in doc.sections:
        units.extend(_section_units(section, doc))

    if not units:
        text = doc.content_text().strip()
        if not text:
            return []
        units = [(text, {"section_id": None, "section_title": None, "heading_path": [], "block_types": ["paragraph"]})]

    packed = _pack_units(units, max_tokens=max_tokens)

    # Merge tiny trailing chunks into previous when under min_tokens
    merged: list[tuple[str, dict]] = []
    for text, meta in packed:
        if merged and approx_tokens(text) < min_tokens:
            prev_text, prev_meta = merged[-1]
            if approx_tokens(prev_text) + approx_tokens(text) <= max_tokens * 1.15:
                merged[-1] = (
                    f"{prev_text}\n\n{text}".strip(),
                    {**prev_meta, "merged_small_followup": True},
                )
                continue
        merged.append((text, meta))

    chunks: list[Chunk] = []
    for index, (content, meta) in enumerate(merged):
        chunks.append(
            Chunk(
                chunk_id=make_chunk_id(ChunkStrategy.STRUCTURAL.value, doc.source_id, index, content),
                document_id=doc.document_id,
                source_id=doc.source_id,
                strategy=ChunkStrategy.STRUCTURAL,
                content=content,
                token_count=approx_tokens(content),
                section_title=meta.get("section_title"),
                section_id=meta.get("section_id"),
                heading_path=list(meta.get("heading_path") or []),
                page_number=meta.get("page_number"),
                document_type=doc.document_type.value,
                family=doc.family,
                source_url=doc.source_url,
                title=doc.title,
                metadata={
                    "max_tokens": max_tokens,
                    "min_tokens": min_tokens,
                    "block_types": meta.get("block_types", []),
                    "atomic_kept": bool(meta.get("atomic")) or bool(meta.get("over_budget")),
                    "over_budget": bool(meta.get("over_budget")),
                    "preserves_structure": True,
                },
            )
        )
    return chunks
