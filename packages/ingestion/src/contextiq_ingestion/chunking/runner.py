from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from contextiq_ingestion.chunking.evaluate import evaluate_strategy, load_golden
from contextiq_ingestion.chunking.fixed import chunk_fixed
from contextiq_ingestion.chunking.models import Chunk, ChunkStrategy
from contextiq_ingestion.chunking.semantic import chunk_semantic
from contextiq_ingestion.chunking.structural import chunk_structural
from contextiq_ingestion.config import default_clean_dir, repo_root
from contextiq_ingestion.models import CleanDocument

logger = logging.getLogger(__name__)

ChunkFn = Callable[[CleanDocument], list[Chunk]]


def default_chunks_dir() -> Path:
    return repo_root() / "corpus" / "chunks"


def load_clean_documents(clean_dir: Path | None = None) -> list[CleanDocument]:
    root = clean_dir or default_clean_dir()
    docs: list[CleanDocument] = []
    for path in sorted(root.glob("*.json")):
        if path.name == "manifest.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.pop("content_text", None)
        docs.append(CleanDocument.model_validate(payload))
    return docs


def strategy_fn(name: str, *, chunk_size: int = 500, overlap_ratio: float = 0.15) -> ChunkFn:
    if name == ChunkStrategy.FIXED.value:
        return lambda doc: chunk_fixed(doc, chunk_size=chunk_size, overlap_ratio=overlap_ratio)
    if name == ChunkStrategy.STRUCTURAL.value:
        return lambda doc: chunk_structural(doc, max_tokens=chunk_size)
    if name == ChunkStrategy.SEMANTIC.value:
        return lambda doc: chunk_semantic(doc, max_tokens=chunk_size)
    raise ValueError(f"Unknown strategy: {name}")


def write_chunks(chunks: list[Chunk], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk.model_dump_json() + "\n")
    return out_path


def load_chunks(path: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunks.append(Chunk.model_validate_json(line))
    return chunks


def run_chunking(
    *,
    strategies: list[str] | None = None,
    families: set[str] | None = None,
    clean_dir: Path | None = None,
    chunks_dir: Path | None = None,
    chunk_size: int = 500,
    overlap_ratio: float = 0.15,
) -> dict[str, list[Chunk]]:
    docs = load_clean_documents(clean_dir)
    if families:
        docs = [d for d in docs if (d.family or "") in families]
    if not docs:
        raise RuntimeError("No clean documents found — run contextiq-ingest first")

    selected = strategies or [
        ChunkStrategy.FIXED.value,
        ChunkStrategy.STRUCTURAL.value,
        ChunkStrategy.SEMANTIC.value,
    ]
    out_root = chunks_dir or default_chunks_dir()
    results: dict[str, list[Chunk]] = {}

    for name in selected:
        fn = strategy_fn(name, chunk_size=chunk_size, overlap_ratio=overlap_ratio)
        all_chunks: list[Chunk] = []
        for doc in docs:
            produced = fn(doc)
            all_chunks.extend(produced)
            logger.info("%s / %s → %s chunks", name, doc.source_id, len(produced))
        path = out_root / name / "chunks.jsonl"
        write_chunks(all_chunks, path)
        manifest = {
            "strategy": name,
            "document_count": len(docs),
            "chunk_count": len(all_chunks),
            "avg_tokens": round(
                sum(c.token_count for c in all_chunks) / max(len(all_chunks), 1), 1
            ),
            "by_family": _count_by(all_chunks),
        }
        (out_root / name / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        results[name] = all_chunks
        logger.info("wrote %s (%s chunks)", path, len(all_chunks))
    return results


def _count_by(chunks: list[Chunk]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for c in chunks:
        counts[c.family or "unknown"] += 1
    return dict(counts)


def run_chunk_eval(
    *,
    strategies: list[str] | None = None,
    chunks_dir: Path | None = None,
    families_filter_chunks: set[str] | None = None,
    ks: tuple[int, ...] = (5, 10),
    results_path: Path | None = None,
) -> dict[str, Any]:
    """
    Evaluate each strategy's chunks against golden.jsonl.

    Default: use all chunks (Next.js/FastAPI act as distractors — realistic).
    Pass families_filter_chunks={'aws','sst'} for an easier AWS-only ablation.
    """
    selected = strategies or [
        ChunkStrategy.FIXED.value,
        ChunkStrategy.STRUCTURAL.value,
        ChunkStrategy.SEMANTIC.value,
    ]
    root = chunks_dir or default_chunks_dir()
    golden = load_golden()
    comparison: dict[str, Any] = {
        "ks": list(ks),
        "golden_size": len(golden),
        "strategies": {},
    }

    for name in selected:
        path = root / name / "chunks.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Missing chunks for {name}: {path}. Run contextiq-chunk first.")
        chunks = load_chunks(path)
        if families_filter_chunks:
            chunks = [c for c in chunks if (c.family or "") in families_filter_chunks]
        metrics = evaluate_strategy(chunks, golden, ks=ks)
        comparison["strategies"][name] = metrics
        logger.info(
            "%s recall@5=%s recall@10=%s chunks=%s",
            name,
            metrics["metrics"].get("recall@5"),
            metrics["metrics"].get("recall@10"),
            metrics["chunk_count"],
        )

    # Rank by recall@5
    ranked = sorted(
        comparison["strategies"].items(),
        key=lambda kv: kv[1]["metrics"].get("recall@5", 0),
        reverse=True,
    )
    comparison["winner"] = ranked[0][0] if ranked else None
    comparison["ranking"] = [
        {"strategy": name, "recall@5": data["metrics"].get("recall@5"), "recall@10": data["metrics"].get("recall@10")}
        for name, data in ranked
    ]

    out = results_path or (repo_root() / "docs" / "eval-results" / "chunking-comparison.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    # Store without huge per_question dumps in the main file? Keep them — useful. Maybe strip for ADR.
    out.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    logger.info("wrote %s (winner=%s)", out, comparison["winner"])
    return comparison
