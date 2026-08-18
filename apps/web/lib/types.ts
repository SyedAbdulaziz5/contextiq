export type Citation = {
  claim_span: string;
  source_id: string;
  chunk_key?: string | null;
  doc_source_id?: string | null;
  title?: string | null;
  section_title?: string | null;
  source_url?: string | null;
  snippet?: string | null;
};

export type SourceRef = {
  source_id: string;
  chunk_key: string;
  doc_source_id: string;
  title?: string | null;
  section_title?: string | null;
  source_url?: string | null;
  family?: string | null;
  score?: number | null;
  snippet: string;
  channels: string[];
  similarity?: number | null;
  rerank_score?: number | null;
  sparse_score?: number | null;
  rrf_score?: number | null;
};

export type TracePayload = {
  trace_id: string;
  query: string;
  rewritten_query?: string | null;
  route: string;
  stages: { name: string; latency_ms: number }[];
  retrieval_scores: {
    chunk_key: string;
    source_id: string;
    title?: string | null;
    section_title?: string | null;
    score?: number;
    similarity?: number | null;
    rerank_score?: number | null;
    channels?: string[];
  }[];
  citations?: {
    source_id: string;
    claim_span?: string;
    doc_source_id?: string | null;
    chunk_key?: string | null;
    title?: string | null;
    section_title?: string | null;
  }[];
  answer_preview?: string;
  total_latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  cost?: {
    usd: number;
    pricing_key: string;
    label: string;
    billing: string;
    note: string;
    input_tokens: number;
    output_tokens: number;
    input_usd_per_m: number;
    output_usd_per_m: number;
  };
  refused: boolean;
  grounded: boolean;
  confidence: string;
  feedback?: string | null;
  generator?: string;
  retrieval_skipped?: boolean;
  meta?: Record<string, unknown>;
};

export type FinalPayload = {
  query: string;
  route: string;
  rewrite: string | null;
  retrieval_skipped: boolean;
  answer: string;
  display_answer: string;
  citations: Citation[];
  confidence: string;
  insufficient_context: boolean;
  grounded?: boolean;
  sources: SourceRef[];
  meta: Record<string, unknown>;
  trace_id?: string | null;
  trace?: TracePayload | null;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  final?: FinalPayload | null;
  activeCitation?: string | null;
  feedback?: "up" | "down" | null;
};
