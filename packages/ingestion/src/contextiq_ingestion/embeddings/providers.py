from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Sequence

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from contextiq_ingestion.embeddings.mathutil import hashing_embed, l2_normalize

logger = logging.getLogger(__name__)

# Free default: BGE-small (384-d). Hash fallback uses the same dim for cache compatibility.
DEFAULT_DIMS = 384
DEFAULT_SBERT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_BEDROCK_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_BEDROCK_DIMS = 1024


class Embedder(ABC):
    name: str
    dimensions: int

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class LocalHashEmbedder(Embedder):
    """Deterministic hashing embedder — CI / no-download fallback (weak semantics)."""

    def __init__(self, dimensions: int = DEFAULT_DIMS) -> None:
        self.name = f"local-hashing-{dimensions}"
        self.dimensions = dimensions

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [hashing_embed(t, dimensions=self.dimensions) for t in texts]


class SentenceTransformerEmbedder(Embedder):
    """
    Free local semantic embeddings via sentence-transformers.

    Default model: BAAI/bge-small-en-v1.5 (384-d). First run downloads ~130MB.
    """

    def __init__(
        self,
        *,
        model_name: str | None = None,
        device: str | None = None,
        normalize: bool = True,
        batch_size: int = 32,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "sentence-transformers required. "
                "pip install 'contextiq-ingestion[local]'"
            ) from exc

        self.model_name = (
            model_name
            or os.getenv("CONTEXTIQ_SBERT_MODEL")
            or DEFAULT_SBERT_MODEL
        )
        self.normalize = normalize
        self.batch_size = batch_size
        self.name = f"sbert:{self.model_name}"
        logger.info("Loading sentence-transformers model %s …", self.model_name)
        # Prefer local HF cache so serve starts offline (HF often probes missing
        # adapter_config.json and hangs on DNS/network blips).
        offline = os.getenv("CONTEXTIQ_SBERT_OFFLINE", "1").lower() not in {
            "0",
            "false",
            "no",
        }
        try:
            self._model = SentenceTransformer(
                self.model_name, device=device, local_files_only=offline
            )
        except Exception as exc:
            if not offline:
                raise
            logger.warning(
                "Local cache load failed (%s); retrying with network …", exc
            )
            self._model = SentenceTransformer(self.model_name, device=device)
        # Prefer new API; fall back for older sentence-transformers
        if hasattr(self._model, "get_embedding_dimension"):
            self.dimensions = int(self._model.get_embedding_dimension())
        else:
            self.dimensions = int(self._model.get_sentence_embedding_dimension())

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        cleaned = [t if t.strip() else " " for t in texts]
        vectors = self._model.encode(
            list(cleaned),
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=len(cleaned) > 64,
            convert_to_numpy=True,
        )
        out: list[list[float]] = []
        for i, vec in enumerate(vectors):
            if not texts[i].strip():
                out.append([0.0] * self.dimensions)
            else:
                row = [float(x) for x in vec.tolist()]
                out.append(row if self.normalize else l2_normalize(row))
        return out

    def embed_query(self, text: str) -> list[float]:
        # BGE models recommend a query prefix for retrieval
        q = text if not self.model_name.lower().startswith("baai/bge") else f"query: {text}"
        return self.embed_documents([q])[0]


class BedrockThrottlingError(RuntimeError):
    pass


class BedrockTitanEmbedder(Embedder):
    """Optional Amazon Titan embeddings — not required for the free stack."""

    def __init__(
        self,
        *,
        model_id: str | None = None,
        region: str | None = None,
        dimensions: int = DEFAULT_BEDROCK_DIMS,
        normalize: bool = True,
    ) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "boto3 is required for Bedrock embeddings. pip install 'contextiq-ingestion[bedrock]'"
            ) from exc

        self.model_id = model_id or os.getenv(
            "CONTEXTIQ_BEDROCK_EMBED_MODEL", DEFAULT_BEDROCK_MODEL
        )
        self.region = region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
        self.dimensions = dimensions
        self.normalize = normalize
        self.name = self.model_id
        self._client = boto3.client("bedrock-runtime", region_name=self.region)

    @retry(
        retry=retry_if_exception_type(BedrockThrottlingError),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    def _embed_one(self, text: str) -> list[float]:
        body = {
            "inputText": text[:50000],
            "dimensions": self.dimensions,
            "normalize": self.normalize,
        }
        try:
            response = self._client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "Throttling" in msg or "Too many requests" in msg or "429" in msg:
                raise BedrockThrottlingError(msg) from exc
            raise

        payload = json.loads(response["body"].read())
        embedding = payload.get("embedding")
        if not embedding:
            raise RuntimeError(f"Bedrock response missing embedding: keys={list(payload)}")
        vec = [float(x) for x in embedding]
        if len(vec) != self.dimensions:
            raise RuntimeError(f"expected {self.dimensions}-d vector, got {len(vec)}")
        return vec if self.normalize else l2_normalize(vec)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i, text in enumerate(texts):
            if not text.strip():
                out.append([0.0] * self.dimensions)
                continue
            out.append(self._embed_one(text))
            if (i + 1) % 25 == 0:
                logger.info("embedded %s/%s texts via Bedrock", i + 1, len(texts))
        return out


def get_embedder(provider: str | None = None) -> Embedder:
    """
    Defaults to free local sentence-transformers.

    Providers:
      sbert | local | sentence-transformers  → BGE-small (recommended)
      hash | local-hash                      → hashing fallback (CI)
      bedrock | titan                        → optional AWS
    """
    choice = (
        provider or os.getenv("CONTEXTIQ_EMBEDDING_PROVIDER") or "sbert"
    ).lower()
    dims = int(os.getenv("CONTEXTIQ_EMBED_DIMENSIONS", str(DEFAULT_DIMS)))

    if choice in {"sbert", "local", "sentence-transformers", "sentence_transformers"}:
        return SentenceTransformerEmbedder()
    if choice in {"hash", "local-hash", "local_hash"}:
        return LocalHashEmbedder(dimensions=dims)
    if choice in {"bedrock", "titan"}:
        bdims = int(os.getenv("CONTEXTIQ_EMBED_DIMENSIONS", str(DEFAULT_BEDROCK_DIMS)))
        return BedrockTitanEmbedder(dimensions=bdims)
    raise ValueError(
        f"Unknown embedding provider: {choice!r} (use sbert|hash|bedrock)"
    )
