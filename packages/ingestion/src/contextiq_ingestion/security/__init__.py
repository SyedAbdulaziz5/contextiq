"""Security baseline: auth, rate limits, validation, prompt-injection heuristics."""

from __future__ import annotations

from contextiq_ingestion.security.auth import AuthConfig, check_api_key, load_auth_config
from contextiq_ingestion.security.injection import (
    INJECTION_REFUSAL_TEXT,
    is_prompt_injection_attempt,
)
from contextiq_ingestion.security.rate_limit import RateLimiter, load_rate_limit_config
from contextiq_ingestion.security.validation import (
    ValidationError,
    validate_query_body,
)

__all__ = [
    "AuthConfig",
    "INJECTION_REFUSAL_TEXT",
    "RateLimiter",
    "ValidationError",
    "check_api_key",
    "is_prompt_injection_attempt",
    "load_auth_config",
    "load_rate_limit_config",
    "validate_query_body",
]
