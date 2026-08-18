# ContextIQ — free local RAG package

```text
ingest → chunk → embed (SBERT) → hybrid retrieve → generate (Ollama) → eval gate
```

## Install

```bash
pip install -e '.[local,serve,dev]'
```

## Defaults

| Setting | Value |
|---|---|
| `CONTEXTIQ_EMBEDDING_PROVIDER` | `sbert` |
| `CONTEXTIQ_SBERT_MODEL` | `BAAI/bge-small-en-v1.5` |
| `CONTEXTIQ_GENERATOR` | `ollama` (falls back to `extractive`) |

```bash
contextiq-embed upsert --strategy structural --skip-postgres
contextiq-generate ask "What is the Lambda timeout?"
contextiq-serve --port 8787
```

Optional AWS: `pip install -e '.[bedrock]'` and set providers to `bedrock` — not required.
