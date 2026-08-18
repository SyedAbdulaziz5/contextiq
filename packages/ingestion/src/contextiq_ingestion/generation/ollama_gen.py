from __future__ import annotations

import json
import os
from typing import Any

import httpx

from contextiq_ingestion.generation.local import should_refuse
from contextiq_ingestion.generation.models import GroundedAnswer, assemble_context_block, hits_to_source_refs
from contextiq_ingestion.generation.prompts import (
    REFUSAL_TEXT,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from contextiq_ingestion.generation.structured import grounded_from_parsed, parse_json_object
from contextiq_ingestion.retrieval.types import RankedHit
from contextiq_ingestion.security.injection import (
    INJECTION_REFUSAL_TEXT,
    injection_meta_reason,
    is_prompt_injection_attempt,
)

DEFAULT_OLLAMA_MODEL = "llama3.2:1b"
DEFAULT_OLLAMA_BASE = "http://127.0.0.1:11434"


class OllamaGroundedGenerator:
    """
    Free local LLM via Ollama HTTP API.

    Install: https://ollama.com — then `ollama pull llama3.2:1b`
    """

    name = "ollama"

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout_s: float = 120.0,
    ) -> None:
        self.model = model or os.getenv("CONTEXTIQ_OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL
        self.base_url = (
            base_url or os.getenv("CONTEXTIQ_OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE
        ).rstrip("/")
        self.timeout_s = timeout_s
        self.name = f"ollama:{self.model}"

    def available(self) -> bool:
        """True only when the daemon is up *and* the configured model is pulled."""
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            if r.status_code != 200:
                return False
            names = [str(m.get("name") or "") for m in (r.json().get("models") or [])]
            want = self.model
            for n in names:
                if n == want or n.startswith(f"{want}-"):
                    return True
                # allow "llama3.2:1b" to match listed "llama3.2:1b"
                if ":" in want and n.split(":")[0] == want.split(":")[0] and want.split(":", 1)[1] in n:
                    return True
            return False
        except Exception:  # noqa: BLE001
            return False

    def generate(self, question: str, hits: list[RankedHit]) -> GroundedAnswer:
        refs = hits_to_source_refs(hits)
        if is_prompt_injection_attempt(question):
            return GroundedAnswer(
                answer=INJECTION_REFUSAL_TEXT,
                citations=[],
                confidence="none",
                insufficient_context=True,
                sources=refs,
                display_answer=INJECTION_REFUSAL_TEXT,
                meta={"generator": self.name, "reason": injection_meta_reason()},
            )
        if should_refuse(hits):
            return GroundedAnswer(
                answer=REFUSAL_TEXT,
                citations=[],
                confidence="none",
                insufficient_context=True,
                sources=refs,
                display_answer=REFUSAL_TEXT,
                meta={"generator": self.name, "reason": "pre_refuse_low_retrieval"},
            )

        context = assemble_context_block(refs)
        user = USER_PROMPT_TEMPLATE.format(question=question, context=context)
        prompt = f"{SYSTEM_PROMPT}\n\n{user}\n\nRespond with JSON only."

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 1024},
        }
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:  # noqa: BLE001
            return GroundedAnswer(
                answer=REFUSAL_TEXT,
                citations=[],
                confidence="none",
                insufficient_context=True,
                sources=refs,
                display_answer=REFUSAL_TEXT,
                meta={
                    "generator": self.name,
                    "reason": "ollama_error",
                    "error": str(exc)[:300],
                },
            )

        text = str(data.get("response") or "")
        parsed = parse_json_object(text)
        return grounded_from_parsed(parsed, refs, generator=self.name)
