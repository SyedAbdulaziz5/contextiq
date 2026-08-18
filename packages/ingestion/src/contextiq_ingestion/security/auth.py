from __future__ import annotations

import hmac
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthConfig:
    """
    open — demo-friendly; rate limits only (default).
    api_key — require X-API-Key / Authorization: Bearer matching CONTEXTIQ_API_KEY.
    """

    mode: str  # open | api_key
    api_key: str | None


def load_auth_config() -> AuthConfig:
    mode = (os.getenv("CONTEXTIQ_AUTH_MODE") or "open").strip().lower()
    if mode not in {"open", "api_key"}:
        mode = "open"
    key = (os.getenv("CONTEXTIQ_API_KEY") or "").strip() or None
    if mode == "api_key" and not key:
        # Fail closed: api_key mode without a key rejects all protected requests.
        pass
    return AuthConfig(mode=mode, api_key=key)


def check_api_key(headers: dict[str, str], config: AuthConfig | None = None) -> bool:
    """Return True if the request is allowed under the current auth config."""
    cfg = config or load_auth_config()
    if cfg.mode == "open":
        return True
    if not cfg.api_key:
        return False
    provided = _extract_key(headers)
    if not provided:
        return False
    return hmac.compare_digest(provided, cfg.api_key)


def _extract_key(headers: dict[str, str]) -> str | None:
    # Normalize: Starlette headers are case-insensitive Mapping but we accept dicts.
    lower = {str(k).lower(): str(v) for k, v in headers.items()}
    raw = lower.get("x-api-key")
    if raw:
        return raw.strip()
    auth = lower.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


# Paths that stay public even in api_key mode (health + static eval reads for portfolio).
PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/eval/dashboard",
        "/eval/failures",
        "/eval/cost-tradeoffs",
    }
)


def path_requires_auth(path: str, config: AuthConfig | None = None) -> bool:
    cfg = config or load_auth_config()
    if cfg.mode != "api_key":
        return False
    # Strip query string if present
    bare = path.split("?", 1)[0]
    if bare in PUBLIC_PATHS:
        return False
    return True
