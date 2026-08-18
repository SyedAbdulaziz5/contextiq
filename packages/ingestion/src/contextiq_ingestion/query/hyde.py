from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from contextiq_ingestion.retrieval.sparse import tokenize


@dataclass
class HyDEResult:
    query: str
    hypothetical_document: str
    method: str


class HyDEGenerator(ABC):
    name: str

    @abstractmethod
    def generate(self, query: str) -> HyDEResult:
        raise NotImplementedError


class TemplateHyDE(HyDEGenerator):
    """
    Offline HyDE stand-in: expands the question into answer-shaped prose.

    Not as strong as an LLM HyDE, but enables A/B testing the *pipeline*
    (embed hypothetical doc vs embed raw query) without Bedrock.
    """

    name = "template_hyde"

    def generate(self, query: str) -> HyDEResult:
        terms = tokenize(query)
        topic = " ".join(terms[:12]) or query
        doc = (
            f"This documentation section explains {query.strip().rstrip('?')}. "
            f"It covers key concepts related to {topic}, including definitions, "
            f"configuration options, limits, examples, and common pitfalls. "
            f"Readers should understand how {topic} behaves in production, "
            f"what constraints apply, and which APIs or settings are relevant."
        )
        return HyDEResult(query=query, hypothetical_document=doc, method=self.name)


class BedrockHyDE(HyDEGenerator):
    """LLM HyDE via Bedrock (Claude). Optional — requires AWS + bedrock extra."""

    name = "bedrock_hyde"

    def __init__(self, model_id: str | None = None, region: str | None = None) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pip install 'contextiq-ingestion[bedrock]' for Bedrock HyDE") from exc
        self.model_id = model_id or os.getenv(
            "CONTEXTIQ_BEDROCK_CHAT_MODEL", "anthropic.claude-3-haiku-20240307-v1:0"
        )
        self.region = region or os.getenv("AWS_REGION") or "us-east-1"
        self._client = boto3.client("bedrock-runtime", region_name=self.region)

    def generate(self, query: str) -> HyDEResult:
        prompt = (
            "Write a short hypothetical documentation paragraph that would answer "
            f"this question (do not say you lack information):\n\nQuestion: {query}\n\nParagraph:"
        )
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": prompt}],
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
        text = text.strip() or TemplateHyDE().generate(query).hypothetical_document
        return HyDEResult(query=query, hypothetical_document=text, method=self.name)


def get_hyde_generator(provider: str | None = None) -> HyDEGenerator:
    choice = (provider or os.getenv("CONTEXTIQ_HYDE_PROVIDER") or "template").lower()
    if choice in {"template", "local"}:
        return TemplateHyDE()
    if choice in {"bedrock", "llm"}:
        return BedrockHyDE()
    raise ValueError(f"Unknown HyDE provider: {choice}")
