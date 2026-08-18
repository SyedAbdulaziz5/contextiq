# ADR 000 — Corpus choice + evaluation-first

**Status:** Accepted  
**Date:** 2026-08-14  
**Phase:** 0

## Context

Portfolio RAG repos usually start with a chatbot demo and never build a measurable quality bar. Our guide (`RAG_project_guide.txt`) and Phase 0 brief require the opposite: a golden evaluation set before retrieval code.

We also need a real corpus (hundreds of pages), not 10 toy PDFs.

## Decision

1. **Eval-first:** Ship `eval/golden.jsonl` + docs in Phase 0. No retrieval/generation implementation until the golden set covers the required categories.
2. **Corpus:** AWS Lambda + Amazon Bedrock + SST official documentation, catalogued in `corpus/sources.json`.
3. **Stable `source_id`s:** Golden labels reference these IDs; ingestion will use the same IDs as `documents.source_id`.

## Consequences

**Positive**
- Every later change (chunking, hybrid, prompts) has a regression surface.
- Recruiters can verify answers against public AWS/SST docs.
- Stack narrative matches resume (Lambda, Bedrock, SST).

**Negative / tradeoffs**
- Phase 0 has no demo UI — must resist the urge to "just ship a chat box."
- Golden answers can drift if AWS changes quotas; we version notes and re-verify during Phase 1 ingestion.
- Maintaining 50–100 labeled items is work; that work *is* the signal.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Pinecone + LangChain tutorial corpus | Commodity signal; weak interview story |
| Tiny PDF dump (≤10 files) | Does not stress hybrid/table/multi-hop |
| Build chat UI first | Locks you into unmeasured quality |
| Fine-tune instead of RAG | Wrong cost/ops profile for this portfolio goal |
