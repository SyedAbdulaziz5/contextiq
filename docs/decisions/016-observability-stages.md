# ADR 016 — Observability stage timers

## Status

Accepted

## Context

Traces previously lumped work into `route_rewrite_retrieve` + `generate`, so the Observability page could not show trustworthy retrieval vs rerank vs LLM latency.

## Decision

1. Instrument **route**, **rewrite**, **dense**, **sparse**, **rrf**, **rerank**, **generate** with `perf_counter` timers.
2. Persist stages on every `QueryTrace`; aggregates (`avg_stage_ms`) average the same names.
3. Store **citations** on the trace for pipeline inspection alongside retrieval scores.
4. Chat and `/traces` both render a **Request breakdown** (latency slices, tokens, cost, docs, citations, feedback).
5. Local/Ollama/extractive generators report **$0** cost; Bedrock uses the documented token table.

## Consequences

- New asks produce fine-grained stages; older JSONL rows may still show legacy names.
- Restart `contextiq-serve` to pick up instrumentation.

## References

- `apps/web/components/RequestBreakdown.tsx`
