# ADR 008 — Production polish: visible retrieval + traces

## Status

Accepted (Phase 8)

## Context

Phases 0–7 proved the RAG system technically. Recruiters still need a **usable demo**: polished chat, visible retrieval, eval UI, and operability signals.

## Decision

1. **Next.js + TypeScript + Tailwind** for the demo UI (chat, eval, traces).
2. **Sources panel** surfaces similarity + rerank scores so hybrid retrieval is visible.
3. **Structured QueryTrace** per request (JSONL under `local/`), with latency, tokens, cost estimate, refusal, and feedback.
4. **API endpoints** for health, streaming query, traces, feedback, and eval dashboard payload.

## Consequences

- Demo path is clickable without reading Python CLIs.
- Traces stay local/gitignored until a later Postgres/Langfuse phase.
- Local generator cost remains $0; Bedrock pricing constants are explicit and adjustable.
