from __future__ import annotations

import re

INJECTION_REFUSAL_TEXT = (
    "I won't follow instructions that try to override system rules or extract secrets. "
    "Ask a documentation question grounded in the corpus instead."
)

# Patterns that try to hijack the assistant (user text or retrieved text).
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?)", re.I),
    re.compile(r"you\s+are\s+now\s+(?:in\s+)?(?:DAN|developer\s+mode|jailbreak)", re.I),
    re.compile(r"system\s*prompt\s*:", re.I),
    re.compile(r"new\s+instructions?\s*:", re.I),
    re.compile(r"override\s+(?:the\s+)?(?:system|safety)\s+(?:prompt|rules?)", re.I),
    re.compile(r"reveal\s+(?:your\s+)?(?:system\s+)?prompt", re.I),
    re.compile(r"(?:secret|private)\s+api\s*key", re.I),
    re.compile(r"exfiltrat", re.I),
]


def is_prompt_injection_attempt(text: str) -> bool:
    """Heuristic flag for override / secret-exfil style prompts (baseline, not a firewall)."""
    if not text or not text.strip():
        return False
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def injection_meta_reason() -> str:
    return "prompt_injection_guard"
