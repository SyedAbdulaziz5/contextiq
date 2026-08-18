"use client";

import type { FinalPayload } from "@/lib/types";
import { buildGroundingView } from "@/lib/grounding";

type Props = {
  final: FinalPayload;
  onSelectSource?: (sourceId: string) => void;
};

export function GroundingPanel({ final, onSelectSource }: Props) {
  const g = buildGroundingView(final);

  if (g.refused) {
    return (
      <div className="mt-3 border border-warn/40 bg-warn-soft px-4 py-3">
        <p className="text-[0.7rem] font-bold uppercase tracking-wider text-warn">
          Insufficient evidence
        </p>
        <p className="mt-1 text-sm font-semibold text-ink">
          ContextIQ refused to answer — the corpus does not support this question reliably.
        </p>
        <p className="mt-2 text-xs text-ink-muted">
          Confidence: <strong className="capitalize text-ink">{g.confidence}</strong>
          {" · "}
          Supporting sources: <strong className="text-ink">0</strong>
        </p>
      </div>
    );
  }

  return (
    <div className="mt-3 border border-line bg-paper-elev/80 px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
          Grounding
        </p>
        {g.grounded ? (
          <span className="rounded bg-accent-soft px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wide text-accent">
            Grounded
          </span>
        ) : (
          <span className="rounded bg-warn-soft px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wide text-warn">
            Weak
          </span>
        )}
      </div>

      <dl className="mt-2 grid grid-cols-3 gap-3 text-sm">
        <div>
          <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
            Confidence
          </dt>
          <dd className="font-semibold capitalize text-ink">{g.confidence}</dd>
        </div>
        <div>
          <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
            Sources
          </dt>
          <dd className="font-semibold tabular-nums text-ink">{g.supportingSources}</dd>
        </div>
        <div>
          <dt className="text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
            Citations
          </dt>
          <dd className="font-semibold tabular-nums text-ink">{g.citationCount}</dd>
        </div>
      </dl>

      <p className="mt-2 text-xs leading-relaxed text-ink-muted">{g.summary}</p>
      <p className="mt-1 text-[0.65rem] text-ink-muted">
        Click a <span className="font-semibold text-accent">[n]</span> chip to highlight the claim
        and open the source.
      </p>

      {g.weakSources.length ? (
        <div className="mt-3 border-t border-line pt-3">
          <p className="text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
            Weaker neighbors in the set
          </p>
          <ul className="mt-1.5 space-y-1">
            {g.weakSources.map((w) => (
              <li key={w.source_id} className="text-xs text-ink-muted">
                <button
                  type="button"
                  onClick={() => onSelectSource?.(w.source_id)}
                  className="font-semibold text-ink hover:text-accent hover:underline"
                >
                  {w.label}
                </button>
                <span className="text-ink-muted"> — {w.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
