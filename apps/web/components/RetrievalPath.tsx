"use client";

type Props = {
  highlight?: boolean;
};

const STAGES = ["Dense", "Sparse", "RRF", "Rerank"] as const;

/** Compact retrieval path for the 60s demo (step 3). */
export function RetrievalPath({ highlight }: Props) {
  return (
    <div
      id="retrieval-path"
      className={`border p-4 text-sm transition-shadow ${
        highlight
          ? "border-accent bg-accent-soft/50 shadow-[0_0_0_1px_rgba(15,92,76,0.25)]"
          : "border-line bg-paper-elev"
      }`}
    >
      <h2 className="font-display text-base font-semibold">Retrieval path</h2>
      <p className="mt-1 text-xs text-ink-muted">How hits are fused before the answer.</p>
      <ol className="mt-3 flex flex-wrap items-center gap-1.5 text-xs font-semibold">
        {STAGES.map((label, i) => (
          <li key={label} className="flex items-center gap-1.5">
            <span className="rounded-sm bg-accent-soft px-2 py-1 text-accent">{label}</span>
            {i < STAGES.length - 1 ? <span className="text-ink-muted">→</span> : null}
          </li>
        ))}
      </ol>
    </div>
  );
}
