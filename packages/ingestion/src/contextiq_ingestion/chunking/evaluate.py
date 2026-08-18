from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from contextiq_ingestion.chunking.models import Chunk, approx_tokens
from contextiq_ingestion.config import repo_root


_TOKEN = re.compile(r"[a-z0-9_./:+-]+", re.I)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text) if len(t) > 1]


@dataclass
class GoldenItem:
    id: str
    question: str
    expected_source_ids: list[str]
    category: str


def load_golden(path: Path | None = None) -> list[GoldenItem]:
    golden_path = path or (repo_root() / "eval" / "golden.jsonl")
    items: list[GoldenItem] = []
    for line in golden_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        items.append(
            GoldenItem(
                id=row["id"],
                question=row["question"],
                expected_source_ids=list(row.get("expected_source_ids") or []),
                category=row["category"],
            )
        )
    return items


class BM25Index:
    """Minimal BM25 for chunk retrieval eval (no extra dependency)."""

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.docs = [_tokenize(c.content) for c in chunks]
        self.doc_len = [len(d) or 1 for d in self.docs]
        self.avgdl = sum(self.doc_len) / max(len(self.doc_len), 1)
        self.df: Counter[str] = Counter()
        for toks in self.docs:
            self.df.update(set(toks))
        self.n = len(self.docs)

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        q_terms = _tokenize(query)
        scores = [0.0] * self.n
        for i, toks in enumerate(self.docs):
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
        out: list[tuple[Chunk, float]] = []
        for i in ranked[:k]:
            if scores[i] <= 0:
                break
            out.append((self.chunks[i], scores[i]))
        return out


def source_recall_at_k(
    retrieved: Iterable[Chunk],
    expected_source_ids: list[str],
) -> float:
    if not expected_source_ids:
        return 0.0
    got = {c.source_id for c in retrieved}
    hit = sum(1 for s in expected_source_ids if s in got)
    return hit / len(expected_source_ids)


def evaluate_strategy(
    chunks: list[Chunk],
    golden: list[GoldenItem],
    *,
    ks: tuple[int, ...] = (5, 10),
) -> dict[str, Any]:
    """
    Measure source-level Context Recall@k using BM25 over chunks.

    Only items with non-empty expected_source_ids are scored (answerable / grounded).
    Unanswerable/ambiguous-empty rows are counted separately.
    """
    index = BM25Index(chunks)
    answerable = [g for g in golden if g.expected_source_ids]
    skipped = len(golden) - len(answerable)

    per_k: dict[str, list[float]] = {f"recall@{k}": [] for k in ks}
    by_category: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    per_question: list[dict[str, Any]] = []

    max_k = max(ks)
    for item in answerable:
        hits = index.search(item.question, k=max_k)
        retrieved_chunks = [c for c, _ in hits]
        row: dict[str, Any] = {
            "id": item.id,
            "category": item.category,
            "expected_source_ids": item.expected_source_ids,
            "retrieved_source_ids": [c.source_id for c in retrieved_chunks[: max(ks)]],
        }
        for k in ks:
            recall = source_recall_at_k(retrieved_chunks[:k], item.expected_source_ids)
            per_k[f"recall@{k}"].append(recall)
            by_category[item.category][f"recall@{k}"].append(recall)
            row[f"recall@{k}"] = round(recall, 4)
        per_question.append(row)

    def avg(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 4) if xs else 0.0

    category_metrics = {
        cat: {metric: avg(vals) for metric, vals in metrics.items()}
        for cat, metrics in sorted(by_category.items())
    }

    token_counts = [c.token_count or approx_tokens(c.content) for c in chunks]
    table_chunks = sum(
        1
        for c in chunks
        if "table" in (c.metadata.get("block_types") or [])
        or "| ---" in c.content
        or c.content.count("|") >= 4
    )

    return {
        "chunk_count": len(chunks),
        "answerable_questions": len(answerable),
        "skipped_no_expected_sources": skipped,
        "metrics": {name: avg(vals) for name, vals in per_k.items()},
        "by_category": category_metrics,
        "chunk_stats": {
            "avg_tokens": round(sum(token_counts) / max(len(token_counts), 1), 1),
            "p50_tokens": sorted(token_counts)[len(token_counts) // 2] if token_counts else 0,
            "p95_tokens": sorted(token_counts)[int(len(token_counts) * 0.95)] if token_counts else 0,
            "max_tokens": max(token_counts) if token_counts else 0,
            "table_like_chunks": table_chunks,
            "sources_covered": len({c.source_id for c in chunks}),
        },
        "per_question": per_question,
    }
