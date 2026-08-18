# Security baseline

Abuse controls for ContextIQ serve. See [ADR 018](decisions/018-security-model.md).

## Auth modes

| Mode | Env | Behavior |
|------|-----|----------|
| `open` (default) | `CONTEXTIQ_AUTH_MODE=open` | No API key; rate limits on `/query` and `/query/stream` |
| `api_key` | `CONTEXTIQ_AUTH_MODE=api_key` + `CONTEXTIQ_API_KEY=…` | Key required on query/traces/feedback |

Headers: `X-API-Key: <key>` or `Authorization: Bearer <key>`.

Public even in `api_key` mode: `/health`, `/eval/*`.

## Rate limits

`CONTEXTIQ_RATE_LIMIT_PER_MINUTE` (default `30`). Set `0` to disable (tests).

429 responses include `Retry-After`.

## Input limits

| Env | Default |
|-----|---------|
| `CONTEXTIQ_MAX_QUERY_CHARS` | 2000 |
| `CONTEXTIQ_MAX_HISTORY_TURNS` | 20 |
| `CONTEXTIQ_MAX_HISTORY_TURN_CHARS` | 2000 |
| `CONTEXTIQ_MAX_TOP_K` | 20 |

## Prompt injection

- System prompt: ignore overrides; treat user + retrieved text as data.
- User prompt wraps context in `BEGIN_CONTEXT` / `END_CONTEXT`.
- Generators pre-refuse heuristic injection / secret-exfil prompts.
- Eval: `eval/golden.jsonl` id `q066`.

This is a **baseline**, not a guarantee against sophisticated attacks.

## CORS

`CONTEXTIQ_CORS_ORIGINS` — comma-separated. Default localhost:3000.

## Secrets

Copy `.env.example` → `.env`. Never commit `.env` or real keys. Rotate production keys yourself (manual).
