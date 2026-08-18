from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from contextiq_ingestion.config import (
    default_catalog_db,
    default_clean_dir,
    default_raw_dir,
    load_catalog,
)
from contextiq_ingestion.fetch import FetchError, fetch_source
from contextiq_ingestion.models import CleanDocument, DocumentType, SourceSpec
from contextiq_ingestion.parsers import parse_raw_file
from contextiq_ingestion.store import summarize_docs, upsert_catalog, write_clean_document, write_manifest

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    succeeded: list[CleanDocument] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed and bool(self.succeeded)


def filter_sources(
    sources: list[SourceSpec],
    *,
    families: set[str] | None = None,
    source_ids: set[str] | None = None,
    limit: int | None = None,
) -> list[SourceSpec]:
    selected = sources
    if families:
        selected = [s for s in selected if (s.family or "") in families]
    if source_ids:
        selected = [s for s in selected if s.id in source_ids]
    if limit is not None:
        selected = selected[:limit]
    return selected


def ingest_source(
    source: SourceSpec,
    *,
    raw_dir: Path,
    clean_dir: Path,
    force_fetch: bool = False,
) -> CleanDocument:
    raw_path = fetch_source(source, raw_dir, force=force_fetch)
    doc = parse_raw_file(raw_path, source)
    if not doc.content_text().strip():
        raise RuntimeError(f"Parsed document is empty: {source.id}")
    write_clean_document(doc, clean_dir)
    return doc


def run_ingestion(
    *,
    families: set[str] | None = None,
    source_ids: set[str] | None = None,
    limit: int | None = None,
    force_fetch: bool = False,
    raw_dir: Path | None = None,
    clean_dir: Path | None = None,
    catalog_db: Path | None = None,
    skip_catalog: bool = False,
) -> IngestResult:
    catalog = load_catalog()
    sources = filter_sources(
        catalog.sources,
        families=families,
        source_ids=source_ids,
        limit=limit,
    )
    if not sources:
        raise RuntimeError("No sources matched the given filters")

    raw = raw_dir or default_raw_dir()
    clean = clean_dir or default_clean_dir()
    db = catalog_db or default_catalog_db()
    raw.mkdir(parents=True, exist_ok=True)
    clean.mkdir(parents=True, exist_ok=True)

    result = IngestResult()
    for source in sources:
        try:
            doc = ingest_source(source, raw_dir=raw, clean_dir=clean, force_fetch=force_fetch)
            result.succeeded.append(doc)
            logger.info(
                "ingested %s (%s sections, %s chars, type=%s)",
                source.id,
                doc.section_count(),
                len(doc.content_text()),
                doc.document_type.value,
            )
        except (FetchError, Exception) as exc:  # noqa: BLE001
            logger.exception("failed %s", source.id)
            result.failed.append({"source_id": source.id, "error": str(exc)})

    if result.succeeded:
        write_manifest(result.succeeded, clean)
        if not skip_catalog:
            upsert_catalog(result.succeeded, db)

    summary = summarize_docs(result.succeeded)
    logger.info("ingestion summary: %s", summary)
    if result.failed:
        logger.warning("failed sources: %s", result.failed)
    return result


def smoke_parse_formats() -> dict[str, bool]:
    """Tiny self-check that parsers accept fixture-like snippets (no network)."""
    from contextiq_ingestion.parsers import parse_markdown_file
    import tempfile

    md = """---
title: Fixture Doc
---

# Hello

Intro paragraph.

## Quotas

| Resource | Limit |
| --- | --- |
| Timeout | 15 minutes |

- item one
- item two

```python
print("hi")
```
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fixture.md"
        path.write_text(md, encoding="utf-8")
        source = SourceSpec(
            id="fixture",
            title="Fixture",
            url="https://example.com",
            format=DocumentType.MARKDOWN,
            family="test",
        )
        doc = parse_markdown_file(path, source)
        has_table = any(b.type == "table" for s in doc.sections for b in s.content_blocks)
        has_list = any(b.type == "list" for s in doc.sections for b in s.content_blocks)
        has_code = any(b.type == "code" for s in doc.sections for b in s.content_blocks)
        return {
            "sections": doc.section_count() >= 2,
            "table": has_table,
            "list": has_list,
            "code": has_code,
        }
