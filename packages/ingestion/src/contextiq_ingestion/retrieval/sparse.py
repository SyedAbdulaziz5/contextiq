from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol

from contextiq_ingestion.retrieval.types import RankedHit


_TOKEN = re.compile(r"[a-z0-9_./:+-]+", re.I)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text) if len(t) > 1]


class HasContent(Protocol):
    chunk_key: str
    source_id: str
    content: str
    section_title: str | None
    family: str | None
    source_url: str | None
    title: str | None


class SparseBM25Retriever:
    """In-memory BM25 (same family as Postgres ts_rank) for keyword/exact-token retrieval."""

    def __init__(self, docs: list[HasContent], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(d.content) for d in docs]
        self.doc_len = [len(t) or 1 for t in self.tokens]
        self.avgdl = sum(self.doc_len) / max(len(self.doc_len), 1)
        self.df: Counter[str] = Counter()
        for toks in self.tokens:
            self.df.update(set(toks))
        self.n = len(self.docs)

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        family: str | None = None,
    ) -> list[RankedHit]:
        q_terms = tokenize(query)
        scores = [0.0] * self.n
        for i, toks in enumerate(self.tokens):
            doc = self.docs[i]
            if family and doc.family != family:
                continue
            tf = Counter(toks)
            dl = self.doc_len[i]
            score = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                freq = tf[term]
                idf = self._idf(term)
                denom = freq + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                score += idf * (freq * (self.k1 + 1)) / denom
            scores[i] = score

        ranked = sorted(range(self.n), key=lambda i: scores[i], reverse=True)
        hits: list[RankedHit] = []
        for rank, i in enumerate(ranked, start=1):
            if scores[i] <= 0:
                break
            if len(hits) >= top_k:
                break
            doc = self.docs[i]
            hits.append(
                RankedHit(
                    chunk_key=doc.chunk_key,
                    source_id=doc.source_id,
                    content=doc.content,
                    score=scores[i],
                    rank=rank,
                    section_title=doc.section_title,
                    family=doc.family,
                    source_url=doc.source_url,
                    title=doc.title,
                    channels=["sparse"],
                )
            )
        return hits
