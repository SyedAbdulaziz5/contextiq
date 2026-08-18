# ADR 010 — Free local stack (no AWS required)

## Status

Accepted

## Context

The original guide suggested Bedrock + Lambda + SST. For a portfolio demo without AWS access or budget, that stack adds cost and credential friction without improving the RAG learning story.

## Decision

1. **Default embeddings:** `sentence-transformers` (`BAAI/bge-small-en-v1.5`, 384-d).
2. **Default generation:** Ollama (`llama3.2:1b`) with JSON grounded schema; **extractive** fallback if Ollama is unavailable.
3. **Hash embedder** retained as `CONTEXTIQ_EMBEDDING_PROVIDER=hash` for CI (no model download).
4. **Bedrock / boto3** remain optional extras only.
5. Docs and README describe the free stack as the primary path.

## Consequences

- First `pip install '.[local]'` + model download needs network once (~130MB for BGE-small).
- Embedding cache must be rebuilt after switching from hashing → SBERT.
- Postgres schema uses `VECTOR(384)` to match BGE-small.
- Interview narrative: “I optimized for RAG quality and a zero-cost demo; cloud providers are swappable behind the same interfaces.”
