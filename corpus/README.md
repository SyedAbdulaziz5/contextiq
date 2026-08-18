# Corpus

| File / dir | Tracked? | Purpose |
|---|---|---|
| `sources.json` | yes | Canonical source catalog (`source_id`, URLs, family, format) |
| `raw/` | no | Exact downloaded bytes/text |
| `clean/` | no | Structure-preserved JSON per document + `manifest.json` |
| `catalog.sqlite` | no | Local document/section index |

Regenerate artifacts:

```bash
cd packages/ingestion
source .venv/bin/activate
contextiq-ingest
```

See `packages/ingestion/README.md`.
