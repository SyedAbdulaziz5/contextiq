from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Route(str, Enum):
    GREETING = "greeting"
    META = "meta"  # what can you do / capabilities
    CALCULATION = "calculation"
    CLARIFY = "clarification"
    RAG = "rag"


@dataclass
class RouteDecision:
    route: Route
    confidence: float
    reason: str
    reply: str | None = None  # canned response when not RAG


_GREETING = re.compile(
    r"^\s*(hi|hello|hey|yo|howdy|good\s+(morning|afternoon|evening)|thanks|thank you|thx)\b[\s!.?]*$",
    re.I,
)
_META = re.compile(
    r"^\s*(what can you do|who are you|how do you work|what is this|help|your capabilities)\b",
    re.I,
)
_CALC = re.compile(
    r"^\s*(?:what(?:'s| is)\s+)?(\d+\s*[\+\-\*/×÷]\s*\d+(?:\s*[\+\-\*/×÷]\s*\d+)*)\s*\??\s*$",
    re.I,
)
_AMBIGUOUS = re.compile(
    r"^\s*("
    r"what about (it|that|this|them|those|the (second|first|third|last|other|previous) one)"
    r"|and (that|this|the second one)"
    r"|tell me more(?: about (it|that|this))?"
    r"|more|why|how"
    r")\s*\??\s*$",
    re.I,
)


def _safe_eval_math(expr: str) -> str | None:
    cleaned = (
        expr.lower()
        .replace("×", "*")
        .replace("÷", "/")
        .replace("x", "*")
        .replace("what is", "")
        .replace("what's", "")
        .strip(" ?")
    )
    if not re.fullmatch(r"[\d\.\+\-\*/\(\)\s]+", cleaned):
        return None
    try:
        value = eval(cleaned, {"__builtins__": {}}, {})  # noqa: S307 — restricted arithmetic only
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value)
    except Exception:  # noqa: BLE001
        return None


class QueryRouter:
    """
    Cheap, deterministic router — no LLM required.

    Greeting / meta / calc / clarify skip retrieval (save latency + cost).
    Everything else goes to RAG.
    """

    def route(self, query: str, *, has_history: bool = False) -> RouteDecision:
        q = query.strip()
        if not q:
            return RouteDecision(
                Route.CLARIFY,
                1.0,
                "empty query",
                "Could you ask a documentation question? For example: “What is the Lambda timeout?”",
            )

        if _GREETING.match(q):
            return RouteDecision(
                Route.GREETING,
                0.95,
                "matches greeting pattern",
                "Hi — I’m ContextIQ. Ask me about the ingested docs (Next.js, FastAPI, AWS Lambda/Bedrock, SST).",
            )

        if _META.search(q):
            return RouteDecision(
                Route.META,
                0.9,
                "capability / meta question",
                "I retrieve from your documentation corpus with hybrid search (dense + keyword → RRF → rerank), "
                "then answer with citations. Try: “What is amazon.titan-embed-text-v2:0?” or “How do layouts work in Next.js?”",
            )

        calc = _CALC.match(q)
        if calc:
            result = _safe_eval_math(calc.group(1))
            if result is not None:
                return RouteDecision(
                    Route.CALCULATION,
                    0.9,
                    "arithmetic expression",
                    f"{calc.group(1).strip()} = {result}",
                )

        # Ambiguous follow-ups without history need clarification
        if _AMBIGUOUS.match(q) and not has_history:
            return RouteDecision(
                Route.CLARIFY,
                0.85,
                "underspecified without conversation context",
                "I need a bit more context — what topic or document are you referring to?",
            )

        # Very short non-doc pings
        if len(q.split()) <= 2 and not re.search(r"[a-z0-9]+[._:-][a-z0-9]+", q, re.I):
            if q.lower() in {"ok", "okay", "cool", "nice", "lol", "sup"}:
                return RouteDecision(Route.GREETING, 0.7, "short chitchat", "👍 What would you like to look up in the docs?")

        return RouteDecision(Route.RAG, 0.8, "treated as documentation question", None)
