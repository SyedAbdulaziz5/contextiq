"use client";

import type { TracePayload } from "@/lib/types";

const STAGE_LABELS: Record<string, string> = {
  route: "Route",
  rewrite: "Rewrite",
  hyde: "HyDE",
  dense: "Dense retrieve",
  sparse: "Sparse retrieve",
  rrf: "RRF fuse",
  rerank: "Rerank",
  retrieve_total: "Retrieve (total)",
  generate: "Generate / LLM",
  route_rewrite_retrieve: "Route+retrieve (legacy)",
};

type Props = {
  trace: TracePayload;
  compact?: boolean;
};

function stageMs(trace: TracePayload, names: string[]): number | null {
  const stages = trace.stages || [];
  let sum = 0;
  let hit = false;
  for (const n of names) {
    const row = stages.find((s) => s.name === n);
    if (row) {
      sum += row.latency_ms;
      hit = true;
    }
  }
  return hit ? sum : null;
}

export function RequestBreakdown({ trace, compact }: Props) {
  const retrieval =
    stageMs(trace, ["dense", "sparse", "rrf"]) ??
    stageMs(trace, ["retrieve_total"]) ??
    stageMs(trace, ["route_rewrite_retrieve"]);
  const rerank = stageMs(trace, ["rerank"]);
  const generate = stageMs(trace, ["generate"]);
  const routeRewrite = stageMs(trace, ["route", "rewrite"]);

  return (
    <div className={`border border-line bg-paper-elev ${compact ? "p-3" : "p-4"}`}>
      <h2 className={`font-display font-semibold ${compact ? "text-sm" : "text-base"}`}>
        Request breakdown
      </h2>
      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
        <div>
          <dt className="text-ink-muted">Route / rewrite</dt>
          <dd className="font-semibold tabular-nums">
            {routeRewrite != null ? `${routeRewrite.toFixed(0)} ms` : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-ink-muted">Retrieval</dt>
          <dd className="font-semibold tabular-nums">
            {retrieval != null ? `${retrieval.toFixed(0)} ms` : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-ink-muted">Rerank</dt>
          <dd className="font-semibold tabular-nums">
            {rerank != null ? `${rerank.toFixed(0)} ms` : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-ink-muted">Generate</dt>
          <dd className="font-semibold tabular-nums">
            {generate != null ? `${generate.toFixed(0)} ms` : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-ink-muted">Total</dt>
          <dd className="font-semibold tabular-nums">{trace.total_latency_ms.toFixed(0)} ms</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Cost</dt>
          <dd className="font-semibold tabular-nums">${Number(trace.cost_usd).toFixed(5)}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Tokens in→out</dt>
          <dd className="font-semibold tabular-nums">
            {trace.input_tokens}→{trace.output_tokens}
          </dd>
        </div>
        <div>
          <dt className="text-ink-muted">Feedback</dt>
          <dd className="font-semibold">{trace.feedback || "—"}</dd>
        </div>
        <div>
          <dt className="text-ink-muted">Model</dt>
          <dd className="font-semibold">{trace.cost?.label || trace.generator || "—"}</dd>
        </div>
      </dl>

      {trace.cost?.note ? (
        <p className="mt-2 text-[0.7rem] leading-snug text-ink-muted">{trace.cost.note}</p>
      ) : null}

      {trace.cost && trace.cost.billing === "per_token" ? (
        <p className="mt-1 text-[0.65rem] text-ink-muted">
          Rate: ${trace.cost.input_usd_per_m}/1M in · ${trace.cost.output_usd_per_m}/1M out
        </p>
      ) : null}

      {!compact && (trace.stages?.length || 0) > 0 ? (
        <ul className="mt-3 space-y-1 border-t border-line pt-3 text-xs">
          {trace.stages.map((s) => (
            <li key={s.name} className="flex justify-between gap-2">
              <span className="text-ink-muted">{STAGE_LABELS[s.name] || s.name}</span>
              <span className="tabular-nums font-semibold">{s.latency_ms.toFixed(1)} ms</span>
            </li>
          ))}
        </ul>
      ) : null}

      {!compact && trace.retrieval_scores?.length ? (
        <div className="mt-3 border-t border-line pt-3">
          <p className="text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
            Retrieved ({trace.retrieval_scores.length})
          </p>
          <ul className="mt-1 max-h-28 space-y-0.5 overflow-y-auto text-xs text-ink-muted">
            {trace.retrieval_scores.map((s) => (
              <li key={s.chunk_key} className="truncate">
                {s.title || s.section_title || s.source_id}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {!compact && trace.citations?.length ? (
        <div className="mt-3 border-t border-line pt-3">
          <p className="text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
            Citations ({trace.citations.length})
          </p>
          <ul className="mt-1 space-y-0.5 text-xs text-ink-muted">
            {trace.citations.map((c, i) => (
              <li key={`${c.source_id}-${i}`} className="truncate">
                {c.source_id}
                {c.claim_span ? ` — “${c.claim_span.slice(0, 48)}”` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export { STAGE_LABELS };
