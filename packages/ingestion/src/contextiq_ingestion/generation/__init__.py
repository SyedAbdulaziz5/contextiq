"""Phase 6 — grounded generation with machine-parseable citations."""

from contextiq_ingestion.generation.models import Citation, GroundedAnswer, SourceRef
from contextiq_ingestion.generation.pipeline import GroundedChatPipeline, build_chat_pipeline

__all__ = [
    "Citation",
    "GroundedAnswer",
    "SourceRef",
    "GroundedChatPipeline",
    "build_chat_pipeline",
]
