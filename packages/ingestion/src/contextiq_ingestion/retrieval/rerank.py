from __future__ import annotations

import math
import re
from collections import Counter

from contextiq_ingestion.retrieval.sparse import tokenize
from contextiq_ingestion.retrieval.types import RankedHit


_ID_LIKE = re.compile(r"[a-z0-9]+(?:[._:-][a-z0-9]+)+", re.I)


class FeatureReranker:
    """
    Lightweight cross-style reranker (no GPU / no Cohere required).

    Combines:
    - query–document term overlap (BM25-ish on the candidate set)
    - exact ID / model-id / dotted-token bonuses (where sparse usually wins)
    - soft preference for shorter, focused chunks

    Swap later for Cohere Rerank or sentence-transformers CrossEncoder via the same interface.
    """

    def __init__(self, *, id_bonus: float = 2.5, length_penalty: float = 0.0005) -> None:
        self.id_bonus = id_bonus
        self.length_penalty = length_penalty

    def rerank(self, query: str, candidates: list[RankedHit], *, top_k: int = 8) -> list[RankedHit]:
        if not candidates:
            return []
        q_terms = tokenize(query)
        q_ids = {m.group(0).lower() for m in _ID_LIKE.finditer(query)}
        q_set = set(q_terms)

        # candidate-set IDF
        df: Counter[str] = Counter()
        docs_toks = [tokenize(c.content) for c in candidates]
        for toks in docs_toks:
            df.update(set(toks))
        n = len(candidates)

        scored: list[tuple[float, RankedHit]] = []
        for cand, toks in zip(candidates, docs_toks):
            tf = Counter(toks)
            overlap = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                overlap += idf * (1.0 + math.log(tf[term]))

            content_l = cand.content.lower()
            exact_ids = sum(1 for i in q_ids if i in content_l)
            # also reward exact rare tokens present as whole words
            exact_terms = sum(1 for t in q_set if re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", content_l))

            # preserve signal from prior fusion rank lightly
            prior = 1.0 / (10 + cand.rank)

            score = (
                overlap
                + self.id_bonus * exact_ids
                + 0.35 * exact_terms
                + prior
                - self.length_penalty * len(toks)
            )
            scored.append((score, cand))

        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[RankedHit] = []
        for rank, (score, cand) in enumerate(scored[:top_k], start=1):
            channels = list(dict.fromkeys([*cand.channels, "rerank"]))
            out.append(
                RankedHit(
                    chunk_key=cand.chunk_key,
                    source_id=cand.source_id,
                    content=cand.content,
                    score=score,
                    rank=rank,
                    section_title=cand.section_title,
                    family=cand.family,
                    source_url=cand.source_url,
                    title=cand.title,
                    channels=channels,
                    metadata={**cand.metadata, "rerank_score": score, "pre_rerank_rank": cand.rank},
                )
            )
        return out
