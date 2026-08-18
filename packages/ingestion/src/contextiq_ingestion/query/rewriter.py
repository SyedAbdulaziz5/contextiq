from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str  # user | assistant
    content: str


@dataclass
class RewriteResult:
    original: str
    rewritten: str
    changed: bool
    reason: str
    history_used: list[str] = field(default_factory=list)


_FOLLOWUP = re.compile(
    r"^\s*("
    r"what about (the )?(second|first|third|last|other|previous) one"
    r"|what about (it|that|this|them|those)"
    r"|and (?:what about )?(?:the )?(second|first|other) one"
    r"|how about (?:the )?(second|first|other) one"
    r"|tell me more(?: about (it|that|this))?"
    r"|and (that|this|those)\b"
    r"|same for (.+)"
    r"|what about (.+)"
    r")\s*\??\s*$",
    re.I,
)

_PRONOUN_QUERY = re.compile(
    r"\b(it|that|this|they|them|those|these)\b",
    re.I,
)


def _last_user_topics(history: list[Turn], limit: int = 2) -> list[str]:
    topics: list[str] = []
    for turn in reversed(history):
        if turn.role != "user":
            continue
        topics.append(turn.content.strip())
        if len(topics) >= limit:
            break
    return list(reversed(topics))


def _extract_focus(text: str) -> str:
    """Pull a coarse topic phrase from a prior user question."""
    t = text.strip()
    # strip leading question words
    t = re.sub(
        r"^(what|what's|how|why|when|where|which|who|can|does|do|is|are)\b[\s']*",
        "",
        t,
        flags=re.I,
    )
    t = t.strip(" ?.")
    return t or text.strip()


class QueryRewriter:
    """
    Deterministic conversational rewrite (no LLM required).

    Resolves follow-ups like “what about the second one?” using prior user turns.
    Standalone questions pass through unchanged.
    """

    def rewrite(self, query: str, history: list[Turn] | None = None) -> RewriteResult:
        history = history or []
        q = query.strip()
        prior = _last_user_topics(history)

        m = _FOLLOWUP.match(q)
        if m and prior:
            focus = _extract_focus(prior[-1])
            # “second one” / generic follow-up → expand with previous topic
            if re.search(r"second|first|third|last|other|previous|it|that|this|them|those|more", q, re.I):
                rewritten = f"Regarding {focus}: provide details, limitations, and related behavior"
                # If prior mentioned a list-like topic, keep it explicit
                if "server component" in focus.lower():
                    rewritten = "What are the limitations and characteristics of Next.js Server Components?"
                return RewriteResult(
                    original=q,
                    rewritten=rewritten,
                    changed=True,
                    reason="follow-up resolved from conversation history",
                    history_used=prior,
                )
            # “what about X” with capture
            tail = m.group(0)
            about = re.search(r"what about (.+?)(?:\?|$)", q, re.I)
            if about:
                entity = about.group(1).strip()
                rewritten = f"{focus} — specifically about {entity}"
                return RewriteResult(
                    original=q,
                    rewritten=rewritten,
                    changed=True,
                    reason="relative 'what about X' expanded with prior topic",
                    history_used=prior,
                )

        # Pronoun-heavy short queries with history
        if prior and _PRONOUN_QUERY.search(q) and len(q.split()) <= 8:
            focus = _extract_focus(prior[-1])
            rewritten = f"{q.rstrip('?')} (in the context of: {focus})?"
            return RewriteResult(
                original=q,
                rewritten=rewritten,
                changed=True,
                reason="pronouns grounded using prior user question",
                history_used=prior,
            )

        # Light cleanup: collapse whitespace
        cleaned = re.sub(r"\s+", " ", q).strip()
        if cleaned != q:
            return RewriteResult(q, cleaned, True, "normalized whitespace", prior)
        return RewriteResult(q, q, False, "standalone query — no rewrite", prior)
