from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class DocumentType(str, Enum):
    HTML = "html"
    MARKDOWN = "markdown"
    MDX = "mdx"
    PDF = "pdf"


BlockType = Literal["paragraph", "list", "table", "code", "blockquote"]


class ContentBlock(BaseModel):
    type: BlockType
    text: str | None = None
    ordered: bool | None = None
    items: list[str] | None = None
    headers: list[str] | None = None
    rows: list[list[str]] | None = None
    language: str | None = None
    markdown: str | None = None

    def to_plaintext(self) -> str:
        if self.type == "paragraph" and self.text:
            return self.text
        if self.type == "blockquote" and self.text:
            return self.text
        if self.type == "code" and self.text:
            lang = self.language or ""
            return f"```{lang}\n{self.text}\n```"
        if self.type == "list" and self.items:
            bullet = "1." if self.ordered else "-"
            return "\n".join(f"{bullet} {item}" for item in self.items)
        if self.type == "table":
            if self.markdown:
                return self.markdown
            headers = self.headers or []
            rows = self.rows or []
            lines = []
            if headers:
                lines.append(" | ".join(headers))
                lines.append(" | ".join("---" for _ in headers))
            for row in rows:
                lines.append(" | ".join(row))
            return "\n".join(lines)
        return ""


class Section(BaseModel):
    id: str
    heading: str | None = None
    heading_level: int | None = None
    heading_path: list[str] = Field(default_factory=list)
    page_number: int | None = None
    content_blocks: list[ContentBlock] = Field(default_factory=list)

    def to_plaintext(self) -> str:
        parts: list[str] = []
        if self.heading:
            level = self.heading_level or 2
            parts.append("#" * max(1, min(level, 6)) + f" {self.heading}")
        for block in self.content_blocks:
            text = block.to_plaintext().strip()
            if text:
                parts.append(text)
        return "\n\n".join(parts).strip()


class CleanDocument(BaseModel):
    """Structured document written to the clean zone (one JSON file per source)."""

    document_id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    title: str
    source_url: str
    family: str | None = None
    document_type: DocumentType
    last_updated: str | None = None
    fetched_at: str = Field(default_factory=utc_now_iso)
    topics: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    sections: list[Section] = Field(default_factory=list)
    raw_path: str | None = None
    clean_path: str | None = None
    parser: str | None = None
    stats: dict[str, Any] = Field(default_factory=dict)

    def content_text(self) -> str:
        return "\n\n".join(s.to_plaintext() for s in self.sections if s.to_plaintext()).strip()

    def section_count(self) -> int:
        return len(self.sections)

    def block_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for section in self.sections:
            for block in section.content_blocks:
                counts[block.type] = counts.get(block.type, 0) + 1
        return counts


class SourceSpec(BaseModel):
    id: str
    title: str
    url: str
    format: DocumentType = DocumentType.HTML
    family: str | None = None
    fetch_url: str | None = None
    topics: list[str] = Field(default_factory=list)

    def download_url(self) -> str:
        return self.fetch_url or self.url


class CorpusCatalog(BaseModel):
    project: str
    corpus_name: str
    description: str | None = None
    sources: list[SourceSpec]
