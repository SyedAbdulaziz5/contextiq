from __future__ import annotations

import os

from contextiq_ingestion.embeddings.providers import LocalHashEmbedder, get_embedder
from contextiq_ingestion.generation.local import LocalGroundedGenerator
from contextiq_ingestion.generation.pipeline import get_generator


def test_get_embedder_hash_provider(monkeypatch):
    monkeypatch.setenv("CONTEXTIQ_EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("CONTEXTIQ_EMBED_DIMENSIONS", "64")
    emb = get_embedder()
    assert isinstance(emb, LocalHashEmbedder)
    assert emb.dimensions == 64
    vec = emb.embed_query("lambda timeout")
    assert len(vec) == 64


def test_get_generator_extractive(monkeypatch):
    monkeypatch.setenv("CONTEXTIQ_GENERATOR", "extractive")
    gen = get_generator()
    assert isinstance(gen, LocalGroundedGenerator)


def test_get_generator_ollama_falls_back_when_down(monkeypatch):
    monkeypatch.setenv("CONTEXTIQ_GENERATOR", "ollama")
    monkeypatch.setenv("CONTEXTIQ_OLLAMA_BASE_URL", "http://127.0.0.1:9")
    gen = get_generator()
    # Ollama unreachable → extractive fallback
    assert isinstance(gen, LocalGroundedGenerator)
