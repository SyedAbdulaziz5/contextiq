#!/bin/sh
set -eu

ROOT="${CONTEXTIQ_REPO_ROOT:-/app}"
CACHE="${ROOT}/corpus/embeddings/structural/embeddings.jsonl"

if [ ! -f "${CACHE}" ]; then
  echo "contextiq-api: WARNING — missing ${CACHE}"
  echo "  Bake on the host: contextiq-embed upsert --strategy structural --skip-postgres"
  echo "  Then mount corpus/embeddings (see docs/runbook-production.md)."
fi

echo "contextiq-api: auth_mode=${CONTEXTIQ_AUTH_MODE:-open} generator=${CONTEXTIQ_GENERATOR:-extractive} embed=${CONTEXTIQ_EMBEDDING_PROVIDER:-sbert}"
exec "$@"
