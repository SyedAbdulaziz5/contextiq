from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from contextiq_ingestion.embeddings.mathutil import cosine_similarity
from contextiq_ingestion.config import repo_root


@dataclass
class EmbeddedChunk:
    chunk_key: str
    document_id: str
    source_id: str
    strategy: str
    content: str
    embedding: list[float]
    embedding_model: str
    section_title: str | None = None
    section_id: str | None = None
    heading_path: list[str] = field(default_factory=list)
    page_number: int | None = None
    family: str | None = None
    document_type: str | None = None
    source_url: str | None = None
    title: str | None = None
    token_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "chunk_key": self.chunk_key,
            "document_id": self.document_id,
            "source_id": self.source_id,
            "strategy": self.strategy,
            "content": self.content,
            "embedding": self.embedding,
            "embedding_model": self.embedding_model,
            "section_title": self.section_title,
            "section_id": self.section_id,
            "heading_path": self.heading_path,
            "page_number": self.page_number,
            "family": self.family,
            "document_type": self.document_type,
            "source_url": self.source_url,
            "title": self.title,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, row: dict[str, Any]) -> EmbeddedChunk:
        return cls(
            chunk_key=row["chunk_key"],
            document_id=row["document_id"],
            source_id=row["source_id"],
            strategy=row["strategy"],
            content=row["content"],
            embedding=[float(x) for x in row["embedding"]],
            embedding_model=row["embedding_model"],
            section_title=row.get("section_title"),
            section_id=row.get("section_id"),
            heading_path=list(row.get("heading_path") or []),
            page_number=row.get("page_number"),
            family=row.get("family"),
            document_type=row.get("document_type"),
            source_url=row.get("source_url"),
            title=row.get("title"),
            token_count=row.get("token_count"),
            metadata=dict(row.get("metadata") or {}),
        )


def default_embeddings_dir() -> Path:
    return repo_root() / "corpus" / "embeddings"


def cache_path(strategy: str, embeddings_dir: Path | None = None) -> Path:
    root = embeddings_dir or default_embeddings_dir()
    return root / strategy / "embeddings.jsonl"


def write_embedding_cache(rows: list[EmbeddedChunk], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row.to_json(), ensure_ascii=False) + "\n")
    manifest = {
        "strategy": rows[0].strategy if rows else None,
        "count": len(rows),
        "embedding_model": rows[0].embedding_model if rows else None,
        "dimensions": len(rows[0].embedding) if rows else None,
    }
    (path.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def load_embedding_cache(path: Path) -> list[EmbeddedChunk]:
    rows: list[EmbeddedChunk] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(EmbeddedChunk.from_json(json.loads(line)))
    return rows


@dataclass
class SearchHit:
    chunk: EmbeddedChunk
    score: float
    rank: int


class MemoryVectorIndex:
    """In-process cosine search over cached embeddings (offline / no Postgres)."""

    def __init__(self, rows: list[EmbeddedChunk]) -> None:
        self.rows = rows

    def search(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        family: str | None = None,
        source_ids: set[str] | None = None,
        strategy: str | None = None,
    ) -> list[SearchHit]:
        scored: list[tuple[EmbeddedChunk, float]] = []
        for row in self.rows:
            if family and row.family != family:
                continue
            if source_ids and row.source_id not in source_ids:
                continue
            if strategy and row.strategy != strategy:
                continue
            score = cosine_similarity(query_embedding, row.embedding)
            scored.append((row, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        hits: list[SearchHit] = []
        for rank, (row, score) in enumerate(scored[:top_k], start=1):
            hits.append(SearchHit(chunk=row, score=score, rank=rank))
        return hits
