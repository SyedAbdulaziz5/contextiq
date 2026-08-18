from __future__ import annotations

import json
import os
from pathlib import Path

from contextiq_ingestion.models import CorpusCatalog, DocumentType, SourceSpec


def repo_root() -> Path:
    override = (os.getenv("CONTEXTIQ_REPO_ROOT") or "").strip()
    if override:
        return Path(override).resolve()
    # packages/ingestion/src/contextiq_ingestion/config.py -> repo root
    return Path(__file__).resolve().parents[4]


def default_sources_path() -> Path:
    return repo_root() / "corpus" / "sources.json"


def default_raw_dir() -> Path:
    return repo_root() / "corpus" / "raw"


def default_clean_dir() -> Path:
    return repo_root() / "corpus" / "clean"


def default_catalog_db() -> Path:
    return repo_root() / "corpus" / "catalog.sqlite"


def load_catalog(path: Path | None = None) -> CorpusCatalog:
    sources_path = path or default_sources_path()
    raw = json.loads(sources_path.read_text(encoding="utf-8"))
    sources: list[SourceSpec] = []
    for item in raw["sources"]:
        fmt = item.get("format", "html")
        sources.append(
            SourceSpec(
                id=item["id"],
                title=item["title"],
                url=item["url"],
                fetch_url=item.get("fetch_url"),
                family=item.get("family"),
                format=DocumentType(fmt),
                topics=item.get("topics", []),
            )
        )
    return CorpusCatalog(
        project=raw.get("project", "ContextIQ"),
        corpus_name=raw.get("corpus_name", "docs"),
        description=raw.get("description"),
        sources=sources,
    )
