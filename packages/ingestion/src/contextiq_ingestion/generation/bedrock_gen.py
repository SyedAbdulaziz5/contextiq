from __future__ import annotations

import json
import os

from contextiq_ingestion.generation.local import should_refuse
from contextiq_ingestion.generation.models import (
    GroundedAnswer,
    assemble_context_block,
    hits_to_source_refs,
)
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


class BedrockGroundedGenerator:
    """Optional Claude on Bedrock — not required for the free local stack."""

    name = "bedrock-claude"

    def __init__(self, model_id: str | None = None, region: str | None = None) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pip install 'contextiq-ingestion[bedrock]'") from exc
        self.model_id = model_id or os.getenv(
            "CONTEXTIQ_BEDROCK_CHAT_MODEL", "anthropic.claude-3-haiku-20240307-v1:0"
        )
        self.region = region or os.getenv("AWS_REGION") or "us-east-1"
        self._client = boto3.client("bedrock-runtime", region_name=self.region)

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
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user}],
        }
        response = self._client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        payload = json.loads(response["body"].read())
        text = ""
        for block in payload.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        parsed = parse_json_object(text)
        return grounded_from_parsed(parsed, refs, generator=self.name)
