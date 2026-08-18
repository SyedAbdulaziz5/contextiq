# ADR 006 — Grounded generation with parseable citations

## Status

Accepted (Phase 6)

## Context

A RAG chatbot that answers without attributable sources is a demo, not a system. Phase 6 must prove:

1. Answers are constrained to retrieved context.
2. Citations are machine-parseable for an interactive UI.
3. The system refuses when context is insufficient (golden unanswerable set).

## Decision

1. **Tagged context** — top reranked chunks labeled `[S1]`…`[Sn]` with source metadata.
2. **Structured output schema** — JSON with `answer`, `citations[{claim_span, source_id}]`, `confidence`, `insufficient_context`.
3. **Dual generators** — local extractive (offline/CI) and Bedrock Claude (production fluency).
4. **SSE streaming** — Starlette `POST /query/stream` for the Next.js client.
5. **Interactive chips** — UI shows `[n]` chips that expand to title, section, snippet, and original URL — not a plain “Source: docs” footer.
6. **Refusal eval** — `contextiq-generate eval` measures refusal accuracy on `category=unanswerable`.

## Consequences

- Frontend depends on citation IDs, not fragile markdown scraping.
- Local generator is extractive (less fluent) but keeps the pipeline testable without Bedrock.
- Phase 7 can add injection defense and faithfulness checks on the same structured claims.
