# Free local setup (no AWS)

ContextIQ defaults to **free local** providers:

| Piece | Default |
|---|---|
| Embeddings | `sentence-transformers` · `BAAI/bge-small-en-v1.5` (384-d) |
| LLM | Ollama · `llama3.2:1b` (falls back to extractive) |
| API | `contextiq-serve` |
| UI | Next.js |

## One-time setup

```bash
cd packages/ingestion
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[local,serve,dev]'

# Embed corpus (downloads BGE-small ~130MB once)
contextiq-embed upsert --strategy structural --skip-postgres

# Optional fluent LLM (~1.3GB once)
brew install ollama   # or https://ollama.com
brew services start ollama
ollama pull llama3.2:1b
```

Copy env defaults:

```bash
cp .env.example .env
```

Security defaults: **open** demo + rate limits. See [`docs/security.md`](security.md) to lock with an API key.
## Run

```bash
# terminal 1
source packages/ingestion/.venv/bin/activate
contextiq-serve --port 8787

# terminal 2
cd apps/web && npm install && npm run dev
```

Open http://localhost:3000

Until `ollama pull llama3.2:1b` finishes (or if Ollama is down), answers still work via the **extractive** grounded generator — cited, with refusal on ungrounded questions.

## AWS?

Not required. Optional later via `pip install '.[bedrock]'` and
`CONTEXTIQ_EMBEDDING_PROVIDER=bedrock` / `CONTEXTIQ_GENERATOR=bedrock`.
