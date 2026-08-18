from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from contextiq_ingestion.chunking.evaluate import load_golden, source_recall_at_k
from contextiq_ingestion.chunking.models import Chunk
from contextiq_ingestion.chunking.runner import default_chunks_dir, load_chunks
from contextiq_ingestion.config import repo_root
from contextiq_ingestion.embeddings.cache import (
    EmbeddedChunk,
    MemoryVectorIndex,
    cache_path,
    load_embedding_cache,
    write_embedding_cache,
)
from contextiq_ingestion.embeddings.db import PostgresStore, get_database_url
from contextiq_ingestion.embeddings.providers import Embedder, get_embedder

logger = logging.getLogger(__name__)


def chunk_to_embedded(chunk: Chunk, embedding: list[float], model_name: str) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_key=chunk.chunk_id,
        document_id=chunk.document_id,
        source_id=chunk.source_id,
        strategy=chunk.strategy.value if hasattr(chunk.strategy, "value") else str(chunk.strategy),
        content=chunk.content,
        embedding=embedding,
        embedding_model=model_name,
        section_title=chunk.section_title,
        section_id=chunk.section_id,
        heading_path=list(chunk.heading_path),
        page_number=chunk.page_number,
        family=chunk.family,
        document_type=chunk.document_type,
        source_url=chunk.source_url,
        title=chunk.title,
        token_count=chunk.token_count,
        metadata=dict(chunk.metadata),
    )


def embed_chunks(
    chunks: list[Chunk],
    embedder: Embedder,
    *,
    batch_size: int = 32,
) -> list[EmbeddedChunk]:
    rows: list[EmbeddedChunk] = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vectors = embedder.embed_documents([c.content for c in batch])
        for chunk, vec in zip(batch, vectors):
            rows.append(chunk_to_embedded(chunk, vec, embedder.name))
        logger.info("embedded batch %s-%s / %s", i + 1, i + len(batch), len(chunks))
    return rows


def documents_from_chunks(chunks: list[Chunk]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for c in chunks:
        if c.source_id in seen:
            continue
        seen[c.source_id] = {
            "id": c.document_id,
            "source_id": c.source_id,
            "title": c.title,
            "source_url": c.source_url,
            "family": c.family,
            "document_type": c.document_type,
            "metadata": json.dumps({"topics_placeholder": True}),
        }
    return list(seen.values())


def run_upsert(
    *,
    strategy: str = "structural",
    provider: str | None = None,
    chunks_dir: Path | None = None,
    skip_postgres: bool = False,
    batch_size: int = 32,
) -> dict[str, Any]:
    path = (chunks_dir or default_chunks_dir()) / strategy / "chunks.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run: contextiq-chunk run --strategy {strategy}"
        )
    chunks = load_chunks(path)
    embedder = get_embedder(provider)
    logger.info(
        "embedding %s chunks with %s (%sd)",
        len(chunks),
        embedder.name,
        embedder.dimensions,
    )
    rows = embed_chunks(chunks, embedder, batch_size=batch_size)
    cache = write_embedding_cache(rows, cache_path(strategy))
    result: dict[str, Any] = {
        "strategy": strategy,
        "chunks": len(rows),
        "embedding_model": embedder.name,
        "dimensions": embedder.dimensions,
        "cache_path": str(cache),
        "postgres": None,
    }

    if skip_postgres:
        return result

    if not get_database_url():
        logger.warning(
            "DATABASE_URL not set — wrote embedding cache only. "
            "Start infra/docker-compose.yml then re-run without --skip-postgres."
        )
        result["postgres"] = "skipped_no_database_url"
        return result

    store = PostgresStore()
    store.init_schema()
    store.upsert_documents(documents_from_chunks(chunks))
    store.upsert_chunks(rows)
    result["postgres"] = store.stats()
    return result


def run_search(
    query: str,
    *,
    strategy: str = "structural",
    top_k: int = 5,
    family: str | None = None,
    mode: str = "dense",
    provider: str | None = None,
    backend: str = "auto",
) -> list[dict[str, Any]]:
    """
    mode: dense | sparse
    backend: auto | memory | postgres
    """
    embedder = get_embedder(provider)
    use_pg = backend == "postgres" or (backend == "auto" and get_database_url())

    if mode == "sparse":
        if not use_pg:
            raise RuntimeError("sparse (tsvector) search requires Postgres DATABASE_URL")
        store = PostgresStore()
        hits = store.sparse_search(query, top_k=top_k, family=family, strategy=strategy)
    else:
        qvec = embedder.embed_query(query)
        if use_pg:
            store = PostgresStore()
            hits = store.dense_search(qvec, top_k=top_k, family=family, strategy=strategy)
        else:
            cache = cache_path(strategy)
            if not cache.exists():
                raise FileNotFoundError(
                    f"No embedding cache at {cache}. Run: contextiq-embed upsert --strategy {strategy}"
                )
            index = MemoryVectorIndex(load_embedding_cache(cache))
            hits = index.search(qvec, top_k=top_k, family=family, strategy=strategy)

    return [
        {
            "rank": h.rank,
            "score": round(h.score, 4),
            "source_id": h.chunk.source_id,
            "section_title": h.chunk.section_title,
            "family": h.chunk.family,
            "chunk_key": h.chunk.chunk_key,
            "preview": h.chunk.content[:240].replace("\n", " "),
        }
        for h in hits
    ]


def run_dense_eval(
    *,
    strategy: str = "structural",
    ks: tuple[int, ...] = (5, 10),
    provider: str | None = None,
    backend: str = "auto",
) -> dict[str, Any]:
    golden = load_golden()
    answerable = [g for g in golden if g.expected_source_ids]
    embedder = get_embedder(provider)
    use_pg = backend == "postgres" or (backend == "auto" and get_database_url())

    index: MemoryVectorIndex | None = None
    store: PostgresStore | None = None
    if use_pg:
        store = PostgresStore()
    else:
        cache = cache_path(strategy)
        if not cache.exists():
            raise FileNotFoundError(f"Missing embedding cache: {cache}")
        index = MemoryVectorIndex(load_embedding_cache(cache))

    per_k: dict[str, list[float]] = {f"recall@{k}": [] for k in ks}
    max_k = max(ks)

    for item in answerable:
        if store is not None:
            qvec = embedder.embed_query(item.question)
            hits = store.dense_search(qvec, top_k=max_k, strategy=strategy)
        else:
            assert index is not None
            qvec = embedder.embed_query(item.question)
            hits = index.search(qvec, top_k=max_k, strategy=strategy)
        retrieved = [type("C", (), {"source_id": h.chunk.source_id})() for h in hits]
        for k in ks:
            per_k[f"recall@{k}"].append(
                source_recall_at_k(retrieved[:k], item.expected_source_ids)  # type: ignore[arg-type]
            )

    metrics = {
        name: round(sum(vals) / len(vals), 4) if vals else 0.0 for name, vals in per_k.items()
    }
    out = {
        "strategy": strategy,
        "backend": "postgres" if store else "memory",
        "embedding_model": embedder.name,
        "answerable_questions": len(answerable),
        "metrics": metrics,
    }
    path = repo_root() / "docs" / "eval-results" / "dense-retrieval.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out
