from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RankedHit:
    chunk_key: str
    source_id: str
    content: str
    score: float
    rank: int
    section_title: str | None = None
    family: str | None = None
    source_url: str | None = None
    title: str | None = None
    channels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def preview(self, n: int = 220) -> str:
        return self.content[:n].replace("\n", " ")
