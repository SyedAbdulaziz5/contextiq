"""Hybrid retrieval: dense + sparse → RRF → rerank."""

from contextiq_ingestion.retrieval.hybrid import HybridRetriever, build_retriever
from contextiq_ingestion.retrieval.rrf import reciprocal_rank_fusion

__all__ = ["HybridRetriever", "build_retriever", "reciprocal_rank_fusion"]
