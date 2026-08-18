"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchEvalDashboard } from "@/lib/api";
import { CostTradeoffs } from "@/components/CostTradeoffs";

type Failed = {
  id: string;
  category?: string;
  context_recall?: number;
  faithfulness?: number;
  refused?: boolean;
  refusal_correct?: boolean;
  retrieved?: string[];
};

type CompareRow = {
  key: string;
  label: string;
  current: number | null;
  baseline: number | null;
  delta_pp: number | null;
};

type ExperimentDetail = {
  name: string;
  strategy?: string;
  backend?: string;
  retriever?: string;
  reranker?: string;
  mode?: string;
  top_k?: number;
  chunking?: string;
  recall?: number | null;
  faithfulness?: number | null;
  latency_ms_avg?: number | null;
  delta_recall_pp?: number | null;
  delta_latency_ms?: number | null;
  n?: number;
  error?: string;
};

type Dash = {
  title?: string;
  queries_evaluated?: number;
  metrics_pct?: Record<string, number | null>;
  experiments?: { experiment: string; recall: number; faithfulness: number }[];
  experiment_details?: ExperimentDetail[];
  comparison?: CompareRow[];
  baseline?: { ref?: string; metrics_pct?: Record<string, number | null> };
  winner?: string | null;
  production_default?: string | null;
  production_rationale?: string | null;
  notes?: string | null;
  top_k?: number;
  strategy?: string;
  mode?: string;
  failed_queries?: Failed[];
  failed_count?: number;
};

function fmtPct(v: number | null | undefined) {
  return v == null ? "—" : `${v}%`;
}

function Delta({ v }: { v: number | null | undefined }) {
  if (v == null) return <span className="text-ink-muted">—</span>;
  const sign = v > 0 ? "+" : "";
  const color = v > 0 ? "text-accent" : v < 0 ? "text-warn" : "text-ink-muted";
  return (
    <span className={`tabular-nums font-semibold ${color}`}>
      {sign}
      {v} pp
    </span>
  );
}

export function EvalDashboard() {
  const [data, setData] = useState<Dash | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFailed, setShowFailed] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    fetchEvalDashboard()
      .then((d: Dash) => {
        setData(d);
        const details = d.experiment_details || [];
        const prod = details.find((e) => e.name === d.production_default);
        setSelected(prod?.name || details[0]?.name || null);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="font-display text-3xl font-semibold">Evaluation workspace</h1>
        <p className="mt-3 text-ink-muted">
          Run <code className="text-sm">contextiq-eval run</code> and start the API, then refresh.
        </p>
        <p className="mt-2 text-sm text-warn">{error}</p>
      </div>
    );
  }

  if (!data) {
    return <div className="px-4 py-10 text-ink-muted">Loading evaluation…</div>;
  }

  const comparison = data.comparison || [];
  const details = data.experiment_details || [];
  const active = details.find((d) => d.name === selected) || details[0];
  const baselineRef = data.baseline?.ref || "baseline";

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <header className="mb-8 border-b border-line pb-5">
        <p className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
          Knowledge &amp; support intelligence
        </p>
        <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight">
          Evaluation workspace
        </h1>
        <p className="mt-2 text-ink-muted">
          Current run vs <span className="font-semibold text-ink">{baselineRef}</span> — measured on
          the golden set.
        </p>
        <p className="mt-1 text-xs text-ink-muted">
          Pipeline: <code>{data.strategy || "structural"}</code> ·{" "}
          <code>{data.mode || "hybrid_rerank"}</code>
          {data.top_k != null ? (
            <>
              {" "}
              · top-k <code>{data.top_k}</code>
            </>
          ) : null}
          {data.queries_evaluated != null ? (
            <>
              {" "}
              · {data.queries_evaluated} queries
            </>
          ) : null}
        </p>
      </header>

      <section className="border border-line bg-paper-elev/60 p-5">
        <h2 className="font-display text-lg font-semibold">Current vs previous</h2>
        <table className="mt-4 w-full text-sm">
          <thead>
            <tr className="text-left text-[0.7rem] uppercase tracking-wider text-ink-muted">
              <th className="pb-2 font-bold">Metric</th>
              <th className="pb-2 text-right font-bold">Current</th>
              <th className="pb-2 text-right font-bold">{baselineRef}</th>
              <th className="pb-2 text-right font-bold">Δ</th>
            </tr>
          </thead>
          <tbody>
            {comparison.map((row) => (
              <tr key={row.key} className="border-t border-line">
                <td className="py-2.5">{row.label}</td>
                <td className="py-2.5 text-right tabular-nums font-semibold text-accent">
                  {fmtPct(row.current)}
                </td>
                <td className="py-2.5 text-right tabular-nums text-ink-muted">
                  {fmtPct(row.baseline)}
                </td>
                <td className="py-2.5 text-right">
                  <Delta v={row.delta_pp} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.failed_count != null ? (
          <p className="mt-4 text-sm text-ink-muted">
            Weak / failed-ish queries: <strong className="text-ink">{data.failed_count}</strong>
          </p>
        ) : null}
      </section>

      <section className="mt-8">
        <h2 className="font-display text-lg font-semibold">Experiments</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Select a setup for config detail. Deltas are vs production default (
          {data.production_default || "Hybrid + reranker"}).
        </p>

        <div className="mt-4 overflow-x-auto border border-line">
          <table className="w-full min-w-[36rem] text-sm">
            <thead>
              <tr className="border-b border-line bg-paper-elev/80 text-left text-[0.7rem] uppercase tracking-wider text-ink-muted">
                <th className="px-3 py-2 font-bold">Setup</th>
                <th className="px-3 py-2 text-right font-bold">Recall</th>
                <th className="px-3 py-2 text-right font-bold">Faithfulness</th>
                <th className="px-3 py-2 text-right font-bold">Δ Recall</th>
                <th className="px-3 py-2 text-right font-bold">Latency</th>
              </tr>
            </thead>
            <tbody>
              {(details.length
                ? details
                : (data.experiments || []).map(
                    (r): ExperimentDetail => ({
                      name: r.experiment,
                      recall: r.recall,
                      faithfulness: r.faithfulness,
                    }),
                  )
              ).map((row) => {
                const isProd = row.name === data.production_default;
                const isWin = row.name === data.winner;
                const isSel = row.name === active?.name;
                return (
                  <tr
                    key={row.name}
                    className={`cursor-pointer border-t border-line transition-colors hover:bg-accent-soft/50 ${
                      isSel ? "bg-accent-soft/70" : ""
                    }`}
                    onClick={() => setSelected(row.name)}
                  >
                    <td className="px-3 py-2.5 font-semibold">
                      {row.name}
                      {isProd ? (
                        <span className="ml-2 text-[0.65rem] font-bold uppercase tracking-wide text-accent">
                          default
                        </span>
                      ) : null}
                      {isWin && !isProd ? (
                        <span className="ml-2 text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
                          best recall
                        </span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{fmtPct(row.recall)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {fmtPct(row.faithfulness)}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <Delta v={row.delta_recall_pp} />
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-ink-muted">
                      {row.latency_ms_avg != null ? `${row.latency_ms_avg} ms` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {active ? (
          <div className="mt-4 border border-line border-l-accent bg-paper-elev/40 p-4">
            <h3 className="font-display text-base font-semibold">{active.name}</h3>
            <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                  Chunking
                </dt>
                <dd className="font-semibold">{active.chunking || active.strategy || "—"}</dd>
              </div>
              <div>
                <dt className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                  Retriever
                </dt>
                <dd className="font-semibold">{active.retriever || "—"}</dd>
              </div>
              <div>
                <dt className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                  Reranker
                </dt>
                <dd className="font-semibold">{active.reranker || "—"}</dd>
              </div>
              <div>
                <dt className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                  Top-K
                </dt>
                <dd className="font-semibold">{active.top_k ?? data.top_k ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                  Δ Recall vs default
                </dt>
                <dd>
                  <Delta v={active.delta_recall_pp} />
                </dd>
              </div>
              <div>
                <dt className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                  Δ Latency vs default
                </dt>
                <dd className="font-semibold tabular-nums">
                  {active.delta_latency_ms == null ? (
                    <span className="text-ink-muted">—</span>
                  ) : (
                    `${active.delta_latency_ms > 0 ? "+" : ""}${active.delta_latency_ms} ms`
                  )}
                </dd>
              </div>
            </dl>
            {active.error ? <p className="mt-3 text-sm text-warn">{active.error}</p> : null}
          </div>
        ) : null}

        {data.production_rationale ? (
          <p className="mt-4 text-sm leading-relaxed text-ink-muted">{data.production_rationale}</p>
        ) : data.notes ? (
          <p className="mt-4 text-sm leading-relaxed text-ink-muted">{data.notes}</p>
        ) : null}
      </section>

      <div className="mt-6 flex flex-wrap gap-2">
        <Link
          href="/failures"
          className="rounded-md border border-line bg-paper-elev px-3 py-2 text-sm font-semibold hover:border-accent"
        >
          Failure analysis
        </Link>
        <button
          type="button"
          onClick={() => setShowFailed((v) => !v)}
          className="rounded-md border border-line bg-paper-elev px-3 py-2 text-sm font-semibold hover:border-accent"
        >
          {showFailed ? "Hide" : "View"} failed queries
        </button>
      </div>

      {showFailed ? (
        <section className="mt-4 border border-line bg-paper-elev/60 p-4">
          <h2 className="font-display text-lg font-semibold">Failed / weak queries</h2>
          <p className="mt-1 text-xs text-ink-muted">
            Raw list from the latest suite. For narrative + measured fixes, open{" "}
            <Link href="/failures" className="font-semibold text-accent hover:underline">
              Failure analysis
            </Link>
            .
          </p>
          {!data.failed_queries?.length ? (
            <p className="mt-2 text-sm text-ink-muted">
              Start <code>contextiq-serve</code> for failed-query detail, or none matched the
              threshold.
            </p>
          ) : (
            <ul className="mt-3 max-h-80 space-y-2 overflow-y-auto text-sm">
              {data.failed_queries.map((f) => (
                <li key={f.id} className="border border-line px-3 py-2">
                  <div className="font-semibold">{f.id}</div>
                  <div className="text-xs text-ink-muted">
                    {f.category}
                    {f.context_recall != null ? ` · recall ${f.context_recall}` : ""}
                    {f.faithfulness != null ? ` · faith ${f.faithfulness}` : ""}
                    {f.refused ? " · refused" : ""}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      <CostTradeoffs />
    </div>
  );
}
