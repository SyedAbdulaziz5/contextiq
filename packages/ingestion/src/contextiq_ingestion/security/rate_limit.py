from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitConfig:
    per_minute: int
    enabled: bool


def load_rate_limit_config() -> RateLimitConfig:
    raw = os.getenv("CONTEXTIQ_RATE_LIMIT_PER_MINUTE")
    if raw is not None and raw.strip() == "0":
        return RateLimitConfig(per_minute=0, enabled=False)
    per_minute = int(raw or "30")
    return RateLimitConfig(per_minute=max(0, per_minute), enabled=per_minute > 0)


class RateLimiter:
    """In-memory sliding-window limiter (single-process demo / small deploy)."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or load_rate_limit_config()
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        """
        Returns (allowed, retry_after_seconds).
        retry_after is 0 when allowed.
        """
        if not self.config.enabled or self.config.per_minute <= 0:
            return True, 0
        now = time.monotonic()
        window = 60.0
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= window:
                q.popleft()
            if len(q) >= self.config.per_minute:
                retry = max(1, int(window - (now - q[0])) + 1)
                return False, retry
            q.append(now)
            return True, 0


RATE_LIMITED_PATHS = frozenset({"/query", "/query/stream"})
