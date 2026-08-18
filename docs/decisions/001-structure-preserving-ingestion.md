# ADR 001 — Structure-preserving local ingestion (raw → clean)

**Status:** Accepted  
**Date:** 2026-08-14  
**Phase:** 1

## Context

Phase 1 needs a real corpus ingested before chunking/embeddings. The guide describes S3 raw/clean zones; we do not have SST/AWS deploy yet. Phase 0's golden set depends on AWS `source_id`s, while the Phase 1 brief prefers Next.js + FastAPI for a recruiter-friendly demo.

Flattening docs to plain text early destroys tables and heading hierarchy — exactly the content our `table` and multi-section eval questions need.

## Decision

1. **Local raw/clean zones** under `corpus/raw/` and `corpus/clean/` (filesystem stand-ins for future S3).
2. **Multi-family corpus:** Next.js + FastAPI (demo) **and** AWS/SST (golden-set continuity).
3. **Structured clean JSON** per document: `sections[]` with typed `content_blocks` (`paragraph`, `list`, `table`, `code`, `blockquote`) — not a single blob.
4. **SQLite catalog** (`corpus/catalog.sqlite`) stores the Phase 1 fields (`document_id`, `title`, `source_url`, `section`, `page`, `content`, `last_updated`, `document_type`) until Postgres in Phase 3.
5. **Parsers we own:** BeautifulSoup (HTML), frontmatter + custom MD/MDX walker, pypdf (PDF). No LangChain document loaders.

## Consequences

**Positive**
- Chunking (Phase 2) can split on real headings/tables.
- Recruiters can ask Next.js/FastAPI questions; eval still targets AWS labels.
- Re-runnable CLI: `contextiq-ingest`.

**Tradeoffs**
- MDX JSX stripping is best-effort (Next.js docs use custom components).
- Some host paths move; sources.json URLs need occasional fixes.
- Raw/clean artifacts stay local (gitignored) — clone + ingest to regenerate.
