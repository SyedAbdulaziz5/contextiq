# Deploy to Vercel + Railway/Render

This guide covers deploying ContextIQ with the **Next.js frontend on Vercel** and the **Python API on Railway, Render, or Fly**.

> First-time setup only takes ~15 minutes. You need a GitHub account, Vercel account, and one API-host account.

---

## Architecture

```
Browser → Vercel (apps/web, Next.js)
               ↓ NEXT_PUBLIC_API_URL
         Railway / Render (contextiq-serve, Python)
               ↓ reads
         Baked embeddings (volume / object storage)
```

---

## Step 1 — Push to GitHub

```bash
cd ~/Projects/RAG_system
git init
git add .
git commit -m "initial commit"
gh repo create RAG_system --public --source=. --push
# or: git remote add origin https://github.com/YOU/RAG_system && git push -u origin main
```

> Note: corpus artifacts (raw/chunks/embeddings) are in `.gitignore` — they will NOT be pushed. That is correct. See Step 2.

---

## Step 2 — Bake embeddings for the API host

The Python API needs the embedding cache to answer questions.
Run this locally once to produce the files, then upload them (or bake inside CI/deploy):

```bash
cd packages/ingestion
source .venv/bin/activate

# If you haven't already:
contextiq-ingest
contextiq-chunk run --strategy structural
contextiq-embed upsert --strategy structural --skip-postgres

# Files to upload (relative to repo root):
#   corpus/chunks/structural/chunks.jsonl
#   corpus/embeddings/structural/embeddings.jsonl
```

Upload them to your API host's persistent volume, or as a build artefact.

---

## Step 3 — Deploy the Python API (Railway recommended)

### Option A: Railway (Railpack)

This is a **monorepo**. Railpack looks at the **repo root**. Leave **Root Directory empty** (`/`). Do not set it to `apps/web`.

The repo includes:

- `requirements.txt` — so Railpack detects Python
- `railpack.json` — Python 3.12 + start command
- `Procfile` — `contextiq-serve --host 0.0.0.0 --port $PORT`

Redeploy after those files are on GitHub.

**Railway service settings**

| Setting | Value |
|---|---|
| Root Directory | *(empty / repo root)* |
| Builder | Railpack (default) |
| Start command | *(leave empty — railpack.json / Procfile)* |

**Environment variables** (do **not** set `PORT` — Railway injects it):

```
CONTEXTIQ_EMBEDDING_PROVIDER=sbert
CONTEXTIQ_GENERATOR=extractive
CONTEXTIQ_AUTH_MODE=open
CONTEXTIQ_CORS_ORIGINS=https://your-app.vercel.app
CONTEXTIQ_REPO_ROOT=/app
```

Optional lock: `CONTEXTIQ_AUTH_MODE=api_key` + `CONTEXTIQ_API_KEY=...`

Add a **volume** and mount baked embeddings at `/app/corpus`.

The `[local]` extra pulls sentence-transformers (and torch). If the build OOMs, bump RAM or switch the extra to `[serve]` and `CONTEXTIQ_EMBEDDING_PROVIDER=hash` for a smoke deploy only.

### Option B: Render

1. New Web Service → connect your GitHub repo.
2. **Build Command:** `pip install -e 'packages/ingestion[serve,local]'`
3. **Start Command:** `contextiq-serve --host 0.0.0.0 --port $PORT`
4. Add the same env vars as above.

### Option C: Fly.io (with Docker)

```bash
fly launch --dockerfile infra/Dockerfile.api \
           --build-arg PIP_EXTRAS=serve,local \
           --name contextiq-api

fly secrets set CONTEXTIQ_AUTH_MODE=api_key \
               CONTEXTIQ_API_KEY=<key> \
               CONTEXTIQ_CORS_ORIGINS=https://your-app.vercel.app \
               CONTEXTIQ_REPO_ROOT=/app

fly volumes create contextiq_data --size 1
fly deploy
```

After deploy, confirm the health endpoint responds:

```bash
curl https://your-api-host.railway.app/health
# → {"status": "ok", "generator": "extractive", ...}
```

---

## Step 4 — Deploy the frontend (Vercel)

1. Go to [vercel.com](https://vercel.com) → **Add New → Project** → import your GitHub repo.
2. Set **Root Directory** to `apps/web`.
3. Framework: **Next.js** (auto-detected).
4. **Environment Variables** to add in Vercel dashboard:

```
NEXT_PUBLIC_API_URL=https://your-api-host.railway.app
```

> If you enabled API key auth on the Python side, also add:
> `NEXT_PUBLIC_API_KEY=<same key as CONTEXTIQ_API_KEY>`
> (demo-only — do not use a secret key here; `NEXT_PUBLIC_*` is visible to the browser.)

5. Click **Deploy**. Vercel builds `apps/web` and publishes.
6. Copy the Vercel URL (e.g. `https://rag-system.vercel.app`).

---

## Step 5 — Wire up CORS

On your Railway/Render/Fly API host, update the env var:

```
CONTEXTIQ_CORS_ORIGINS=https://rag-system.vercel.app
```

Redeploy or restart the API service.

---

## Step 6 — Update vercel.json with your API host

Edit `vercel.json` at repo root and replace `your-api-host.example.com` with your real API hostname:

```json
{
  "rootDirectory": "apps/web",
  "rewrites": [
    {
      "source": "/api/contextiq/:path*",
      "destination": "https://contextiq-api.railway.app/:path*"
    }
  ]
}
```

This optional rewrite lets you proxy the API through Vercel (avoids CORS entirely, hides API URL from browser).

---

## Step 7 — Final smoke test

```bash
# Health
curl https://your-api-host.railway.app/health

# Query (open auth mode)
curl -X POST https://your-api-host.railway.app/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is SST?", "top_k": 3}'

# With API key
curl -X POST https://your-api-host.railway.app/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"query": "What is SST?", "top_k": 3}'
```

Then open the Vercel URL in a browser and confirm:
- Landing page loads
- Chat sends a question and streams a response with citations
- `/eval` page loads metrics

---

## Step 8 — Update README

In `README.md`, replace the placeholder live demo URL:

```md
[Live Demo](https://your-app.vercel.app) · ...
```

Also update the CI badge URLs with your GitHub username:

```md
[![CI](https://github.com/YOUR_GITHUB_USERNAME/RAG_system/actions/workflows/ci.yml/badge.svg)]
```

---

## Environment variable reference

### API host (Railway / Render / Fly)

| Variable | Required | Example |
|---|---|---|
| `CONTEXTIQ_EMBEDDING_PROVIDER` | Yes | `sbert` |
| `CONTEXTIQ_GENERATOR` | Yes | `extractive` |
| `CONTEXTIQ_AUTH_MODE` | No | `api_key` (default: `open`) |
| `CONTEXTIQ_API_KEY` | If api_key mode | `sk-...` |
| `CONTEXTIQ_CORS_ORIGINS` | Yes | `https://your-app.vercel.app` |
| `CONTEXTIQ_REPO_ROOT` | Yes | `/app` |
| `PORT` | Yes (set by host) | `8787` |
| `CONTEXTIQ_RATE_LIMIT_PER_MINUTE` | No | `30` |

### Vercel (apps/web)

| Variable | Required | Example |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | `https://contextiq-api.railway.app` |
| `NEXT_PUBLIC_API_KEY` | Only if api_key mode | same as above key |
| `NEXT_PUBLIC_GITHUB_URL` | No | `https://github.com/you/RAG_system` |

---

## Troubleshooting

**API returns 500 on /query**
: Embeddings are missing. SSH/shell into the host and confirm `corpus/embeddings/structural/embeddings.jsonl` exists. Re-run `contextiq-embed upsert` locally and upload the files.

**CORS error in browser**
: `CONTEXTIQ_CORS_ORIGINS` doesn't include your exact Vercel domain (check `https://` prefix, no trailing slash).

**`NEXT_PUBLIC_API_URL` not picking up in Vercel build**
: Add it in Vercel project → Settings → Environment Variables, then **redeploy** (values are inlined at build time).

**"Address already in use" on Railway**
: Make sure `--port $PORT` is used in start command, not a hardcoded port.
