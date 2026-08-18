from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ChunkStrategy(str, Enum):
    FIXED = "fixed"
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"


def approx_tokens(text: str) -> int:
    """Whitespace token estimate — good enough for chunk budgets; documented in ADR."""
    return max(1, len(text.split())) if text.strip() else 0


def make_chunk_id(strategy: str, source_id: str, index: int, content: str) -> str:
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:10]
    return f"{strategy}:{source_id}:{index:04d}:{digest}"


class Chunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    source_id: str
    strategy: ChunkStrategy
    content: str
    token_count: int = 0
    section_title: str | None = None
    section_id: str | None = None
    heading_path: list[str] = Field(default_factory=list)
    page_number: int | None = None
    document_type: str
    family: str | None = None
    source_url: str
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:  # noqa: ANN401
        if not self.token_count:
            self.token_count = approx_tokens(self.content)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = _SENTENCE_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]
