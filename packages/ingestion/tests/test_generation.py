from __future__ import annotations

from contextiq_ingestion.generation.local import LocalGroundedGenerator, should_refuse
from contextiq_ingestion.generation.models import (
    Citation,
    answer_with_numeric_chips,
    assemble_context_block,
    hits_to_source_refs,
)
from contextiq_ingestion.generation.prompts import REFUSAL_TEXT
from contextiq_ingestion.retrieval.types import RankedHit


def _hit(i: int, content: str, score: float = 2.0) -> RankedHit:
    return RankedHit(
        chunk_key=f"doc#c{i}",
        source_id="nextjs-server-components",
        content=content,
        score=score,
        rank=i,
        section_title="Server Components",
        title="Next.js Documentation",
        source_url="https://nextjs.org/docs/app/building-your-application/rendering/server-components",
        channels=["sparse", "rerank"],
    )


def test_assemble_context_tags():
    refs = hits_to_source_refs([_hit(1, "Server Components render on the server.")])
    block = assemble_context_block(refs)
    assert "[S1]" in block
    assert "Server Components" in block


def test_numeric_chips():
    text = answer_with_numeric_chips(
        "Rendered on the server [S1].",
        [Citation(claim_span="Rendered", source_id="S1")],
    )
    assert "[1]" in text
    assert "[S1]" not in text


def test_local_generator_cites():
    gen = LocalGroundedGenerator()
    hits = [
        _hit(
            1,
            "Server Components are rendered on the server by default. "
            "They can fetch data directly without exposing secrets to the client.",
            score=5.0,
        )
    ]
    out = gen.generate("How are Server Components rendered?", hits)
    assert not out.insufficient_context
    assert out.citations
    assert "[1]" in (out.display_answer or "")


def test_local_generator_refuses_stock():
    gen = LocalGroundedGenerator()
    hits = [_hit(1, "Lambda timeout is 15 minutes.", score=0.5)]
    out = gen.generate("What is the current stock price of Amazon (AMZN)?", hits)
    assert out.insufficient_context
    assert REFUSAL_TEXT in out.answer


def test_should_refuse_empty():
    assert should_refuse([])
