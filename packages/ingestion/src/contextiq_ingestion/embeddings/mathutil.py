from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


_TOKEN = re.compile(r"[a-z0-9_./:+-]+", re.I)


def l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Cosine similarity for equal-length vectors.
    If both are L2-normalized, this equals the dot product.
    pgvector's <=> operator is cosine *distance* = 1 - cosine_similarity.
    """
    if len(a) != len(b):
        raise ValueError(f"vector length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def cosine_distance(a: list[float], b: list[float]) -> float:
    return 1.0 - cosine_similarity(a, b)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text) if len(t) > 1]


def _stable_hash(seed: int, term: str) -> int:
    """Process-stable hash (builtin hash() is randomized per Python process)."""
    digest = hashlib.blake2b(f"{seed}:{term}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def hashing_embed(text: str, dimensions: int = 1024, seed: int = 13) -> list[float]:
    """
    Deterministic local embedder (feature hashing over tokens + char trigrams).

    NOT a substitute for Titan quality — used so Postgres/pgvector plumbing,
    cosine search, and offline eval work without AWS credentials.
    Default quality vectors use CONTEXTIQ_EMBEDDING_PROVIDER=sbert; hash is for CI.
    """
    vec = [0.0] * dimensions
    tokens = tokenize(text)
    compact = re.sub(r"\s+", " ", text.lower())
    trigrams = [compact[i : i + 3] for i in range(max(0, len(compact) - 2))]
    features = tokens + trigrams
    if not features:
        return l2_normalize(vec)
    counts = Counter(features)
    for term, count in counts.items():
        h = _stable_hash(seed, term)
        idx = h % dimensions
        sign = 1.0 if (h & 1) == 0 else -1.0
        weight = 1.0 if len(term) <= 3 else (1.0 + math.log(count))
        vec[idx] += sign * weight
    return l2_normalize(vec)
