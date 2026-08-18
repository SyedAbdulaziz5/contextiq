"use client";

import { useEffect, useState } from "react";
import { fetchCostTradeoffs } from "@/lib/api";

type Setup = {
  name: string;
  recall_pct?: number | null;
  faithfulness_pct?: number | null;
  latency_note?: string;
  est_cost_usd_per_query?: number;
  generator?: string;
};

type Comparison = {
  id: string;
  title: string;
  setup_a: Setup;
  setup_b: Setup;
  delta?: { recall_pp?: number; cost_usd?: number };
  verdict?: string;
  source?: string;
};

type PricingRow = {
  key: string;
  label: string;
  note?: string;
  input_usd_per_m?: number;
  output_usd_per_m?: number;
  usd_per_1m_in?: number;
  usd_per_1m_out?: number;
};

type Payload = {
  title?: string;
  comparisons?: Comparison[];
  pricing?: PricingRow[];
  pricing_live?: PricingRow[];
  production_default?: { retrieval?: string; generator?: string; why?: string };
  assumptions_doc?: string;
  error?: string;
};

function rateIn(p: PricingRow) {
  return p.input_usd_per_m ?? p.usd_per_1m_in;
}

function rateOut(p: PricingRow) {
  return p.output_usd_per_m ?? p.usd_per_1m_out;
}

function fmtCost(n: number | undefined) {
  if (n == null) return "—";
  if (n === 0) return "$0";
  return `$${n.toFixed(6)}`;
}

export function CostTradeoffs() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCostTradeoffs()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return <p className="mt-6 text-sm text-warn">{error}</p>;
  }
  if (!data) {
    return <p className="mt-6 text-sm text-ink-muted">Loading cost tradeoffs…</p>;
  }

  const pricing = data.pricing_live || data.pricing || [];

  return (
    <section className="mt-10 border-t border-line pt-8">
      <h2 className="font-display text-xl font-semibold">
        {data.title || "Quality · latency · cost"}
      </h2>
      <p className="mt-1 text-sm text-ink-muted">
        Measured recall where available; costs from{" "}
        <code className="text-xs">{data.assumptions_doc || "docs/cost-model.md"}</code> — no
        invented prices.
      </p>

      {data.production_default ? (
        <p className="mt-3 text-sm text-ink">
          <span className="font-semibold">Production default:</span>{" "}
          {data.production_default.retrieval} · {data.production_default.generator}.{" "}
          <span className="text-ink-muted">{data.production_default.why}</span>
        </p>
      ) : null}

      <div className="mt-4 overflow-x-auto border border-line">
        <table className="w-full min-w-[40rem] text-sm">
          <thead>
            <tr className="border-b border-line bg-paper-elev/80 text-left text-[0.7rem] uppercase tracking-wider text-ink-muted">
              <th className="px-3 py-2 font-bold">Comparison</th>
              <th className="px-3 py-2 font-bold">A</th>
              <th className="px-3 py-2 font-bold">B</th>
              <th className="px-3 py-2 text-right font-bold">Δ Recall</th>
              <th className="px-3 py-2 text-right font-bold">Cost/query</th>
            </tr>
          </thead>
          <tbody>
            {(data.comparisons || []).map((c) => (
              <tr key={c.id} className="border-t border-line align-top">
                <td className="px-3 py-3">
                  <p className="font-semibold text-ink">{c.title}</p>
                  <p className="mt-1 text-xs text-ink-muted">{c.verdict}</p>
                  {c.source ? (
                    <p className="mt-1 text-[0.65rem] text-ink-muted">Source: {c.source}</p>
                  ) : null}
                </td>
                <td className="px-3 py-3 text-xs">
                  <p className="font-semibold">{c.setup_a.name}</p>
                  <p>Recall {c.setup_a.recall_pct ?? "—"}%</p>
                  <p className="text-ink-muted">{fmtCost(c.setup_a.est_cost_usd_per_query)}</p>
                </td>
                <td className="px-3 py-3 text-xs">
                  <p className="font-semibold">{c.setup_b.name}</p>
                  <p>Recall {c.setup_b.recall_pct ?? "—"}%</p>
                  <p className="text-ink-muted">{fmtCost(c.setup_b.est_cost_usd_per_query)}</p>
                </td>
                <td className="px-3 py-3 text-right tabular-nums font-semibold">
                  {c.delta?.recall_pp == null
                    ? "—"
                    : `${c.delta.recall_pp > 0 ? "+" : ""}${c.delta.recall_pp} pp`}
                </td>
                <td className="px-3 py-3 text-right text-xs tabular-nums">
                  {fmtCost(c.setup_a.est_cost_usd_per_query)} →{" "}
                  {fmtCost(c.setup_b.est_cost_usd_per_query)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pricing.length ? (
        <div className="mt-4">
          <p className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
            Pricing table
          </p>
          <ul className="mt-2 space-y-1 text-xs text-ink-muted">
            {pricing.map((p) => (
              <li key={p.key}>
                <span className="font-semibold text-ink">{p.label}</span>
                {" — "}
                ${rateIn(p) ?? "—"}/1M in · ${rateOut(p) ?? "—"}/1M out
                {p.note ? ` · ${p.note}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
