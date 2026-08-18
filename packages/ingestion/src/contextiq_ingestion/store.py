from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contextiq_ingestion.models import CleanDocument


def clean_path_for(clean_dir: Path, source_id: str) -> Path:
    return clean_dir / f"{source_id}.json"


def write_clean_document(doc: CleanDocument, clean_dir: Path) -> Path:
    clean_dir.mkdir(parents=True, exist_ok=True)
    path = clean_path_for(clean_dir, doc.source_id)
    doc.clean_path = str(path)
    payload = doc.model_dump(mode="json")
    # Include flattened content for debugging / later phases (not a substitute for sections)
    payload["content_text"] = doc.content_text()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_manifest(docs: list[CleanDocument], clean_dir: Path) -> Path:
    clean_dir.mkdir(parents=True, exist_ok=True)
    path = clean_dir / "manifest.json"
    items = []
    for doc in docs:
        items.append(
            {
                "document_id": doc.document_id,
                "source_id": doc.source_id,
                "title": doc.title,
                "source_url": doc.source_url,
                "family": doc.family,
                "document_type": doc.document_type.value,
                "section_count": doc.section_count(),
                "block_counts": doc.block_counts(),
                "char_count": len(doc.content_text()),
                "last_updated": doc.last_updated,
                "fetched_at": doc.fetched_at,
                "clean_path": doc.clean_path,
                "raw_path": doc.raw_path,
                "parser": doc.parser,
            }
        )
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "document_count": len(items),
        "documents": items,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
  document_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  source_url TEXT NOT NULL,
  family TEXT,
  section TEXT,
  page INTEGER,
  content TEXT,
  last_updated TEXT,
  document_type TEXT NOT NULL,
  fetched_at TEXT,
  clean_path TEXT,
  raw_path TEXT,
  section_count INTEGER,
  char_count INTEGER,
  metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS sections (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  heading TEXT,
  heading_level INTEGER,
  heading_path TEXT,
  page_number INTEGER,
  content TEXT NOT NULL,
  FOREIGN KEY(document_id) REFERENCES documents(document_id)
);
"""


def upsert_catalog(docs: list[CleanDocument], db_path: Path) -> Path:
    """Local catalog DB mirroring Phase 1 required fields (Postgres arrives in Phase 3)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        for doc in docs:
            conn.execute(
                """
                INSERT INTO documents (
                  document_id, source_id, title, source_url, family, section, page, content,
                  last_updated, document_type, fetched_at, clean_path, raw_path,
                  section_count, char_count, metadata_json
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                  document_id=excluded.document_id,
                  title=excluded.title,
                  source_url=excluded.source_url,
                  family=excluded.family,
                  content=excluded.content,
                  last_updated=excluded.last_updated,
                  document_type=excluded.document_type,
                  fetched_at=excluded.fetched_at,
                  clean_path=excluded.clean_path,
                  raw_path=excluded.raw_path,
                  section_count=excluded.section_count,
                  char_count=excluded.char_count,
                  metadata_json=excluded.metadata_json
                """,
                (
                    doc.document_id,
                    doc.source_id,
                    doc.title,
                    doc.source_url,
                    doc.family,
                    doc.content_text(),
                    doc.last_updated,
                    doc.document_type.value,
                    doc.fetched_at,
                    doc.clean_path,
                    doc.raw_path,
                    doc.section_count(),
                    len(doc.content_text()),
                    json.dumps(doc.metadata),
                ),
            )
            conn.execute("DELETE FROM sections WHERE source_id = ?", (doc.source_id,))
            for section in doc.sections:
                conn.execute(
                    """
                    INSERT INTO sections (
                      id, document_id, source_id, heading, heading_level, heading_path,
                      page_number, content
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        section.id,
                        doc.document_id,
                        doc.source_id,
                        section.heading,
                        section.heading_level,
                        json.dumps(section.heading_path),
                        section.page_number,
                        section.to_plaintext(),
                    ),
                )
        conn.commit()
    finally:
        conn.close()
    return db_path


def summarize_docs(docs: list[CleanDocument]) -> dict[str, Any]:
    by_family: dict[str, int] = {}
    by_type: dict[str, int] = {}
    tables = 0
    lists = 0
    for doc in docs:
        fam = doc.family or "unknown"
        by_family[fam] = by_family.get(fam, 0) + 1
        by_type[doc.document_type.value] = by_type.get(doc.document_type.value, 0) + 1
        counts = doc.block_counts()
        tables += counts.get("table", 0)
        lists += counts.get("list", 0)
    return {
        "documents": len(docs),
        "by_family": by_family,
        "by_type": by_type,
        "table_blocks": tables,
        "list_blocks": lists,
        "total_chars": sum(len(d.content_text()) for d in docs),
    }
