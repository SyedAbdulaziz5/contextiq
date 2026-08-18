# ADR 011 — Product positioning (Knowledge & Support Intelligence)

## Status

Accepted

## Context

After Phases 0–9, ContextIQ was a strong RAG *engineering* demo but still read as a lab/chat-over-docs project. Portfolio advice: keep the technical differentiators, frame it as a **product** recruiters can understand in seconds.

## Decision

1. **Positioning:** ContextIQ is an **eval-first RAG platform for production knowledge and support systems** — not an “AWS docs chatbot.”
2. **Corpus:** May still include AWS/Next.js/FastAPI public docs for evaluation realism; that is sample knowledge, not the product identity.
3. **Web surfaces:**
   - `/` — public landing (hero + how it works + CTAs)
   - `/chat` — interactive demo
   - `/architecture` — in-app architecture story
   - `/eval`, `/traces` — existing measurement/ops surfaces
4. **GitHub CTA:** optional via `NEXT_PUBLIC_GITHUB_URL` (no hard-coded fake URL).

## Consequences

- Recruiters land on product framing before the chat UI.
- Later phases (eval workspace, failures, deploy) deepen the product story without renaming the technical stack.
- Domain/hosting remain Phase 18 (manual).

## References

- `apps/web/app/page.tsx`
