from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Sequence

from contextiq_ingestion.embeddings.cache import EmbeddedChunk, SearchHit

logger = logging.getLogger(__name__)


def default_schema_path() -> Path:
    return Path(__file__).resolve().parents[3] / "sql" / "001_schema.sql"


def get_database_url() -> str | None:
    return os.getenv("DATABASE_URL") or os.getenv("CONTEXTIQ_DATABASE_URL")


def require_psycopg():
    try:
        import psycopg
        from pgvector.psycopg import register_vector
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "psycopg and pgvector are required for Postgres. "
            "pip install 'contextiq-ingestion[postgres]'"
        ) from exc
    return psycopg, register_vector


class PostgresStore:
    """Own the SQL — no LangChain vector wrappers."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or get_database_url()
        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL is not set. Start infra/docker-compose.yml and export DATABASE_URL."
            )
        self._psycopg, self._register_vector = require_psycopg()

    def connect(self):
        conn = self._psycopg.connect(self.database_url)
        self._register_vector(conn)
        return conn

    def init_schema(self, schema_path: Path | None = None) -> None:
        path = schema_path or default_schema_path()
        sql = path.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.execute(sql)
            conn.commit()
        logger.info("applied schema from %s", path)

    def upsert_documents(self, docs: Sequence[dict[str, Any]]) -> int:
        if not docs:
            return 0
        sql = """
        INSERT INTO documents (id, source_id, title, source_url, family, document_type, metadata)
        VALUES (%(id)s, %(source_id)s, %(title)s, %(source_url)s, %(family)s, %(document_type)s, %(metadata)s::jsonb)
        ON CONFLICT (source_id) DO UPDATE SET
          id = EXCLUDED.id,
          title = EXCLUDED.title,
          source_url = EXCLUDED.source_url,
          family = EXCLUDED.family,
          document_type = EXCLUDED.document_type,
          metadata = EXCLUDED.metadata,
          updated_at = now()
        """
        with self.connect() as conn:
            with conn.cursor() as cur:
                for doc in docs:
                    cur.execute(sql, doc)
            conn.commit()
        return len(docs)

    def upsert_chunks(self, rows: Sequence[EmbeddedChunk], batch_size: int = 50) -> int:
        sql = """
        INSERT INTO chunks (
          chunk_key, document_id, source_id, strategy, content, embedding, embedding_model,
          section_title, section_id, heading_path, page_number, family, document_type,
          source_url, title, token_count, metadata
        ) VALUES (
          %(chunk_key)s, %(document_id)s::uuid, %(source_id)s, %(strategy)s, %(content)s, %(embedding)s,
          %(embedding_model)s, %(section_title)s, %(section_id)s, %(heading_path)s, %(page_number)s,
          %(family)s, %(document_type)s, %(source_url)s, %(title)s, %(token_count)s, %(metadata)s::jsonb
        )
        ON CONFLICT (chunk_key) DO UPDATE SET
          document_id = EXCLUDED.document_id,
          source_id = EXCLUDED.source_id,
          strategy = EXCLUDED.strategy,
          content = EXCLUDED.content,
          embedding = EXCLUDED.embedding,
          embedding_model = EXCLUDED.embedding_model,
          section_title = EXCLUDED.section_title,
          section_id = EXCLUDED.section_id,
          heading_path = EXCLUDED.heading_path,
          page_number = EXCLUDED.page_number,
          family = EXCLUDED.family,
          document_type = EXCLUDED.document_type,
          source_url = EXCLUDED.source_url,
          title = EXCLUDED.title,
          token_count = EXCLUDED.token_count,
          metadata = EXCLUDED.metadata,
          updated_at = now()
        """
        import json

        with self.connect() as conn:
            with conn.cursor() as cur:
                for i in range(0, len(rows), batch_size):
                    batch = rows[i : i + batch_size]
                    for row in batch:
                        cur.execute(
                            sql,
                            {
                                "chunk_key": row.chunk_key,
                                "document_id": row.document_id,
                                "source_id": row.source_id,
                                "strategy": row.strategy,
                                "content": row.content,
                                "embedding": row.embedding,
                                "embedding_model": row.embedding_model,
                                "section_title": row.section_title,
                                "section_id": row.section_id,
                                "heading_path": row.heading_path,
                                "page_number": row.page_number,
                                "family": row.family,
                                "document_type": row.document_type,
                                "source_url": row.source_url,
                                "title": row.title,
                                "token_count": row.token_count,
                                "metadata": json.dumps(row.metadata),
                            },
                        )
                    conn.commit()
                    logger.info("upserted chunks %s-%s / %s", i + 1, i + len(batch), len(rows))
        return len(rows)

    def dense_search(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        family: str | None = None,
        strategy: str | None = None,
    ) -> list[SearchHit]:
        """
        Cosine similarity via pgvector:
          distance = embedding <=> query   (cosine distance)
          score    = 1 - distance          (cosine similarity)
        """
        filters = ["embedding IS NOT NULL"]
        params: list[Any] = [query_embedding]
        if family:
            filters.append("family = %s")
            params.append(family)
        if strategy:
            filters.append("strategy = %s")
            params.append(strategy)
        where = " AND ".join(filters)
        params.extend([query_embedding, top_k])

        sql = f"""
        SELECT
          chunk_key, document_id::text, source_id, strategy, content, embedding,
          embedding_model, section_title, section_id, heading_path, page_number,
          family, document_type, source_url, title, token_count, metadata,
          1 - (embedding <=> %s::vector) AS score
        FROM chunks
        WHERE {where}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """
        hits: list[SearchHit] = []
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                for rank, row in enumerate(cur.fetchall(), start=1):
                    chunk = EmbeddedChunk(
                        chunk_key=row[0],
                        document_id=row[1],
                        source_id=row[2],
                        strategy=row[3],
                        content=row[4],
                        embedding=list(row[5]) if row[5] is not None else [],
                        embedding_model=row[6],
                        section_title=row[7],
                        section_id=row[8],
                        heading_path=list(row[9] or []),
                        page_number=row[10],
                        family=row[11],
                        document_type=row[12],
                        source_url=row[13],
                        title=row[14],
                        token_count=row[15],
                        metadata=dict(row[16] or {}),
                    )
                    hits.append(SearchHit(chunk=chunk, score=float(row[17]), rank=rank))
        return hits

    def sparse_search(
        self,
        query: str,
        *,
        top_k: int = 5,
        family: str | None = None,
        strategy: str | None = None,
    ) -> list[SearchHit]:
        """Keyword retrieval using Postgres full-text search (tsvector / ts_rank)."""
        filters = ["content_tsv @@ plainto_tsquery('english', %s)"]
        where_params: list[Any] = [query]
        if family:
            filters.append("family = %s")
            where_params.append(family)
        if strategy:
            filters.append("strategy = %s")
            where_params.append(strategy)
        where = " AND ".join(filters)
        # score query, where params..., limit
        params: list[Any] = [query, *where_params, top_k]

        sql = f"""
        SELECT
          chunk_key, document_id::text, source_id, strategy, content, embedding,
          embedding_model, section_title, section_id, heading_path, page_number,
          family, document_type, source_url, title, token_count, metadata,
          ts_rank_cd(content_tsv, plainto_tsquery('english', %s)) AS score
        FROM chunks
        WHERE {where}
        ORDER BY score DESC
        LIMIT %s
        """
        hits: list[SearchHit] = []
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                for rank, row in enumerate(cur.fetchall(), start=1):
                    chunk = EmbeddedChunk(
                        chunk_key=row[0],
                        document_id=row[1],
                        source_id=row[2],
                        strategy=row[3],
                        content=row[4],
                        embedding=list(row[5]) if row[5] is not None else [],
                        embedding_model=row[6] or "",
                        section_title=row[7],
                        section_id=row[8],
                        heading_path=list(row[9] or []),
                        page_number=row[10],
                        family=row[11],
                        document_type=row[12],
                        source_url=row[13],
                        title=row[14],
                        token_count=row[15],
                        metadata=dict(row[16] or {}),
                    )
                    hits.append(SearchHit(chunk=chunk, score=float(row[17]), rank=rank))
        return hits

    def stats(self) -> dict[str, Any]:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM documents")
                docs = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM chunks")
                chunks = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")
                embedded = cur.fetchone()[0]
                cur.execute(
                    "SELECT strategy, COUNT(*) FROM chunks GROUP BY strategy ORDER BY strategy"
                )
                by_strategy = {r[0]: r[1] for r in cur.fetchall()}
        return {
            "documents": docs,
            "chunks": chunks,
            "embedded_chunks": embedded,
            "by_strategy": by_strategy,
        }
