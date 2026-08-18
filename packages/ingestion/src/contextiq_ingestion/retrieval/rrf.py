from __future__ import annotations

from collections import defaultdict


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    *,
    k: int = 60,
    weights: list[float] | None = None,
) -> list[tuple[str, float]]:
    """
    Reciprocal Rank Fusion (Cormack et al.), optionally weighted per list.

    score(d) = Σ w_i / (k + rank_i(d))  over each ranked list i
    Ranks are 1-based. k≈60 is the common default.

    Why ranks not raw scores? Dense cosine and BM25 scores are not comparable;
    fusion on rank positions avoids brittle score calibration.

    Weights matter when one channel is weak (e.g. local hashing dense):
    down-weight that list so it cannot drown a strong sparse ranking.
    """
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights length must match rankings length")

    scores: dict[str, float] = defaultdict(float)
    for ranking, weight in zip(rankings, weights):
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] += weight / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)
