"use client";

import { useEffect, useState } from "react";
import { fetchTraceStats, fetchTraces } from "@/lib/api";
import type { TracePayload } from "@/lib/types";
import { RequestBreakdown, STAGE_LABELS } from "@/components/RequestBreakdown";

type Stats = {
  n: number;
  avg_latency_ms: number;
  avg_cost_usd: number;
  refusal_rate: number;
  feedback: { up: number; down: number; none: number };
  avg_stage_ms?: Record<string, number>;
};

const PIPELINE_ORDER = [
  "route",
  "rewrite",
  "hyde",
  "dense",
  "sparse",
  "rrf",
  "rerank",
  "generate",
] as const;

export default function TracesPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [traces, setTraces] = useState<TracePayload[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TracePayload | null>(null);

  useEffect(() => {
    Promise.all([fetchTraceStats(), fetchTraces(40)])
      .then(([s, t]) => {
        setStats(s);
        const list = (t.traces || []) as TracePayload[];
        setTraces(list);
        if (list.length) setSelected(list[0]);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <header className="mb-8 border-b border-line pb-5">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Observability</h1>
        <p className="mt-2 max-w-xl text-ink-muted">
          End-to-end traces with real stage timers: route → rewrite → dense/sparse → RRF →
          rerank → generate.
        </p>
      </header>

      {error ? (
        <p className="text-warn">
          {error}. Start the API with <code>contextiq-serve</code>.
        </p>
      ) : null}

      {stats ? (
        <section className="mb-6 grid gap-3 sm:grid-cols-4">
          {[
            ["Queries", String(stats.n)],
            ["Avg latency", `${stats.avg_latency_ms} ms`],
            ["Avg cost", `$${stats.avg_cost_usd}`],
            ["Refusal rate", `${(stats.refusal_rate * 100).toFixed(1)}%`],
          ].map(([label, value]) => (
            <div key={label} className="border border-line bg-paper-elev p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                {label}
              </p>
              <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
            </div>
          ))}
        </section>
      ) : null}

      {stats?.avg_stage_ms && Object.keys(stats.avg_stage_ms).length ? (
        <section className="mb-6 border border-line bg-paper-elev p-4">
          <h2 className="font-display text-lg font-semibold">Avg latency by stage</h2>
          <p className="mt-1 text-xs text-ink-muted">
            Means over stored traces — same timer names as per-request stages.
          </p>
          <ul className="mt-3 space-y-1 text-sm">
            {Object.entries(stats.avg_stage_ms)
              .sort(([a], [b]) => {
                const ia = PIPELINE_ORDER.indexOf(a as (typeof PIPELINE_ORDER)[number]);
                const ib = PIPELINE_ORDER.indexOf(b as (typeof PIPELINE_ORDER)[number]);
                return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
              })
              .map(([name, ms]) => (
                <li
                  key={name}
                  className="flex justify-between border-b border-line py-1 last:border-0"
                >
                  <span className="text-ink-muted">{STAGE_LABELS[name] || name}</span>
                  <span className="tabular-nums font-semibold">{ms} ms</span>
                </li>
              ))}
          </ul>
          {stats.feedback ? (
            <p className="mt-3 text-xs text-ink-muted">
              Feedback — up: {stats.feedback.up} · down: {stats.feedback.down} · none:{" "}
              {stats.feedback.none}
            </p>
          ) : null}
        </section>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="border border-line bg-paper-elev p-4">
          <h2 className="font-display text-lg font-semibold">Recent traces</h2>
          <ul className="mt-3 max-h-[32rem] space-y-2 overflow-y-auto">
            {traces.map((t) => (
              <li key={t.trace_id}>
                <button
                  type="button"
                  onClick={() => setSelected(t)}
                  className={`w-full border px-3 py-2 text-left text-sm transition-colors ${
                    selected?.trace_id === t.trace_id
                      ? "border-accent bg-accent-soft"
                      : "border-line hover:border-accent"
                  }`}
                >
                  <div className="truncate font-semibold">{t.query}</div>
                  <div className="mt-0.5 text-xs text-ink-muted">
                    {t.total_latency_ms?.toFixed?.(0)} ms ·{" "}
                    {t.refused ? "refused" : t.grounded ? "grounded" : "—"} ·{" "}
                    {t.feedback || "no feedback"}
                  </div>
                </button>
              </li>
            ))}
            {!traces.length && !error ? (
              <li className="text-sm text-ink-muted">Ask a question in Chat to create traces.</li>
            ) : null}
          </ul>
        </section>

        <section className="border border-line bg-paper-elev p-4">
          <h2 className="font-display text-lg font-semibold">Pipeline</h2>
          {selected ? (
            <div className="mt-3 space-y-4 text-sm">
              <p className="font-mono text-xs text-ink-muted">{selected.trace_id}</p>

              <ol className="space-y-2">
                <li>
                  <span className="font-semibold text-ink">query</span>
                  <p className="text-ink-muted">{selected.query}</p>
                </li>
                <li className="border-l border-line pl-3">
                  <span className="font-semibold text-ink">rewritten</span>
                  <p className="text-ink-muted">{selected.rewritten_query || "—"}</p>
                </li>
                {(selected.stages || [])
                  .filter((s) =>
                    ["dense", "sparse", "rrf", "rerank", "generate"].includes(s.name),
                  )
                  .map((s) => (
                    <li key={s.name} className="border-l border-line pl-3">
                      <div className="flex justify-between gap-2">
                        <span className="font-semibold text-ink">
                          {STAGE_LABELS[s.name] || s.name}
                        </span>
                        <span className="tabular-nums text-ink-muted">
                          {s.latency_ms.toFixed(1)} ms
                        </span>
                      </div>
                    </li>
                  ))}
                <li className="border-l border-accent pl-3">
                  <span className="font-semibold text-ink">answer</span>
                  <p className="text-ink-muted">
                    {selected.refused
                      ? "Refused — insufficient evidence"
                      : selected.answer_preview || "—"}
                  </p>
                </li>
              </ol>

              <RequestBreakdown trace={selected} />
            </div>
          ) : (
            <p className="mt-3 text-sm text-ink-muted">Select a trace to inspect the pipeline.</p>
          )}
        </section>
      </div>
    </div>
  );
}
