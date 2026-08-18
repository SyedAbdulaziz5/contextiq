-- ContextIQ Phase 3 schema
-- PostgreSQL + pgvector (dense) + tsvector (sparse / keyword)
-- Run via: contextiq-embed init-db
-- Or: psql $DATABASE_URL -f packages/ingestion/sql/001_schema.sql

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY,
  source_id TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  source_url TEXT,
  family TEXT,
  document_type TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chunk_key TEXT NOT NULL UNIQUE,          -- stable id from chunker (strategy:source:idx:hash)
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  source_id TEXT NOT NULL,
  strategy TEXT NOT NULL,
  content TEXT NOT NULL,
  content_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  embedding VECTOR(384),
  embedding_model TEXT,
  section_title TEXT,
  section_id TEXT,
  heading_path TEXT[] NOT NULL DEFAULT '{}',
  page_number INT,
  family TEXT,
  document_type TEXT,
  source_url TEXT,
  title TEXT,
  token_count INT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Cosine distance ops for dense retrieval (<=>)
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx
  ON chunks USING hnsw (embedding vector_cosine_ops);

-- Keyword / BM25-like retrieval
CREATE INDEX IF NOT EXISTS chunks_content_tsv_gin_idx
  ON chunks USING GIN (content_tsv);

CREATE INDEX IF NOT EXISTS chunks_source_id_idx ON chunks (source_id);
CREATE INDEX IF NOT EXISTS chunks_family_idx ON chunks (family);
CREATE INDEX IF NOT EXISTS chunks_strategy_idx ON chunks (strategy);

COMMENT ON TABLE chunks IS 'ContextIQ retrieval units: dense embedding + sparse tsvector in one DB';
COMMENT ON COLUMN chunks.embedding IS 'Default: BGE-small 384-d (sentence-transformers). L2-normalized preferred';
COMMENT ON COLUMN chunks.content_tsv IS 'Generated english tsvector for keyword search (Phase 4 hybrid)';
