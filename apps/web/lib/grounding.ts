import type { Citation, FinalPayload, SourceRef } from "@/lib/types";

export type GroundingView = {
  refused: boolean;
  grounded: boolean;
  confidence: string;
  supportingSources: number;
  citationCount: number;
  weakSources: { source_id: string; label: string; reason: string }[];
  summary: string;
};

function labelFor(s: SourceRef): string {
  return s.section_title || s.title || s.doc_source_id || s.source_id;
}

/** Weak neighbor heuristic from real retrieval scores only — no contradiction math. */
export function weakSourceHints(sources: SourceRef[]): GroundingView["weakSources"] {
  if (!sources.length) return [];
  const sims = sources.map((s) => s.similarity).filter((n): n is number => n != null);
  const reranks = sources
    .map((s) => s.rerank_score ?? s.score)
    .filter((n): n is number => n != null);
  const maxSim = sims.length ? Math.max(...sims) : null;
  const maxRerank = reranks.length ? Math.max(...reranks) : null;

  const weak: GroundingView["weakSources"] = [];
  for (const s of sources) {
    const sim = s.similarity;
    const rr = s.rerank_score ?? s.score;
    if (sim != null && maxSim != null && maxSim > 0 && sim < maxSim * 0.72 && sim < 0.55) {
      weak.push({
        source_id: s.source_id,
        label: labelFor(s),
        reason: `Low dense similarity (${sim.toFixed(2)} vs top ${maxSim.toFixed(2)})`,
      });
      continue;
    }
    if (
      sim == null &&
      rr != null &&
      maxRerank != null &&
      maxRerank > 0 &&
      rr < maxRerank * 0.45
    ) {
      weak.push({
        source_id: s.source_id,
        label: labelFor(s),
        reason: `Weak rerank score (${rr.toFixed(2)} vs top ${maxRerank.toFixed(2)})`,
      });
    }
  }
  return weak.slice(0, 3);
}

export function buildGroundingView(final: FinalPayload): GroundingView {
  const refused = Boolean(final.insufficient_context);
  const citations = final.citations || [];
  const sources = final.sources || [];
  const citedIds = new Set(
    citations.map((c) => c.source_id).filter(Boolean).concat(
      citations.map((c) => c.doc_source_id || "").filter(Boolean),
    ),
  );
  const supporting = sources.filter(
    (s) =>
      citedIds.has(s.source_id) ||
      citedIds.has(s.doc_source_id) ||
      citations.some(
        (c) =>
          c.chunk_key && c.chunk_key === s.chunk_key,
      ),
  );
  const supportingSources = refused
    ? 0
    : supporting.length || (citations.length ? Math.min(citations.length, sources.length) : sources.length);

  const confidence = (final.confidence || (refused ? "none" : "medium")).toLowerCase();
  const grounded = !refused && (Boolean(final.grounded) || citations.length > 0 || sources.length > 0);
  const weakSources = refused ? [] : weakSourceHints(sources);

  let summary: string;
  if (refused) {
    summary = "Insufficient evidence in the knowledge corpus for a reliable answer.";
  } else if (confidence === "high") {
    summary = "Strong overlap between the answer and retrieved context.";
  } else if (confidence === "low") {
    summary = "Answer is grounded but retrieval confidence is limited.";
  } else {
    summary = "Answer is tied to retrieved sources; review citations for details.";
  }

  return {
    refused,
    grounded,
    confidence,
    supportingSources,
    citationCount: citations.length,
    weakSources,
    summary,
  };
}

export function claimSpansForSource(
  citations: Citation[],
  sourceId: string,
): string[] {
  return citations
    .filter((c) => c.source_id === sourceId && c.claim_span?.trim())
    .map((c) => c.claim_span.trim());
}
