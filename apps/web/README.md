# ContextIQ Web

Next.js + TypeScript + Tailwind — product UI for ContextIQ.

## Pages

| Route | What |
|---|---|
| `/` | Landing — product framing, how it works, CTAs |
| `/chat` | Demo chat — use `?demo=1` for the 60-second guided path |
| `/architecture` | Pipeline + engineering decisions |
| `/eval` | Metrics workspace — current vs baseline, experiments |
| `/failures` | Curated failure cases with measured fixes |
| `/traces` | Latency / cost / refusal / pipeline traces + feedback |

## Run

```bash
# API (separate terminal)
cd packages/ingestion && source .venv/bin/activate
contextiq-serve --port 8787

# UI
cp .env.example .env.local
npm install
npm run dev
```

`NEXT_PUBLIC_API_URL` defaults to `http://127.0.0.1:8787`.  
Set `NEXT_PUBLIC_GITHUB_URL` to show the GitHub CTA on the landing page.
