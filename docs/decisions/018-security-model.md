# ADR 018 — Security model for the demo

## Status

Accepted

## Context

A public RAG demo without abuse controls invites scraping, cost blow-ups (if cloud LLM is on), and naive prompt-injection. Portfolio demos still need to stay usable without a login wall.

## Decision

1. **Default auth mode: `open`** — `/query` and `/query/stream` are callable without a key; **rate limits** apply (default 30/min per client).
2. **Optional lock: `CONTEXTIQ_AUTH_MODE=api_key`** — require `X-API-Key` or `Authorization: Bearer` matching `CONTEXTIQ_API_KEY` on non-public routes (`/query*`, `/traces*`, `/feedback`). Health + eval read endpoints stay public for portfolio pages.
3. **Input caps** — max query/history/top_k via env (`CONTEXTIQ_MAX_*`).
4. **Prompt injection (baseline)** — hardened system prompt; context wrapped as untrusted data; heuristic pre-refuse in generators; golden `q066` + unit tests. Not a complete firewall.
5. **Secrets** — only via env (`.env.example`); never commit keys. Browser `NEXT_PUBLIC_API_KEY` is demo-only and discouraged for real secrets.

## Consequences

- Local/dev stays frictionless.
- Public deploy can flip to `api_key` or keep open + rate limit (manual choice).
- Multi-tenant identity (Clerk/Auth.js) is out of scope until needed.

## References

- `docs/security.md`
