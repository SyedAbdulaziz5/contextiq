"use client";

import type { SourceRef } from "@/lib/types";

function fmt(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toFixed(2);
}

type Props = {
  sources: SourceRef[];
};

export function SourcesPanel({ sources }: Props) {
  if (!sources.length) {
    return (
      <div className="rounded-md border border-line bg-paper-elev p-4 text-sm text-ink-muted">
        No retrieved sources for this turn.
      </div>
    );
  }

  return (
    <div className="rounded-md border border-line bg-paper-elev p-4">
      <h2 className="font-display text-base font-semibold">Retrieved Sources</h2>
      <ol className="mt-3 space-y-3">
        {sources.map((s, i) => (
          <li key={s.chunk_key} className="border-t border-line pt-3 first:border-0 first:pt-0">
            <div className="flex items-start gap-2">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-bold text-accent">
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold text-ink">
                  {s.section_title || s.title || s.doc_source_id}
                </p>
                {s.title && s.section_title ? (
                  <p className="truncate text-xs text-ink-muted">{s.title}</p>
                ) : null}
                <dl className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs text-ink-muted">
                  <div>
                    similarity: <span className="font-semibold tabular-nums text-ink">{fmt(s.similarity)}</span>
                  </div>
                  <div>
                    rerank: <span className="font-semibold tabular-nums text-ink">{fmt(s.rerank_score ?? s.score)}</span>
                  </div>
                </dl>
                {s.channels?.length ? (
                  <p className="mt-1 text-[0.7rem] uppercase tracking-wide text-ink-muted">
                    {s.channels.join(" · ")}
                  </p>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
