"""Embeddings + Postgres/pgvector storage (Phase 3)."""

from contextiq_ingestion.embeddings.mathutil import cosine_similarity, l2_normalize
from contextiq_ingestion.embeddings.providers import Embedder, get_embedder

__all__ = ["Embedder", "get_embedder", "cosine_similarity", "l2_normalize"]
