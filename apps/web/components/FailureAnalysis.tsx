"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchFailureCases } from "@/lib/api";

type MetricImpact = {
  metric: string;
  before: number;
  after: number;
  unit?: string;
  before_label?: string;
  after_label?: string;
  source?: string;
  note?: string;
};

type FailureCase = {
  id: string;
  title: string;
  failure_mode?: string;
  status?: string;
  question_id?: string | null;
  question?: string;
  retrieved?: string[];
  expected_sources?: string[];
  observed_behavior?: string;
  expected_behavior?: string;
  fix?: { area?: string; summary?: string };
  metric_impact?: MetricImpact;
  lesson?: string;
};

type Payload = {
  title?: string;
  subtitle?: string;
  cases?: FailureCase[];
  case_count?: number;
  open_count?: number;
  mitigated_count?: number;
  error?: string;
};

function Impact({ m }: { m: MetricImpact }) {
  const delta = Math.round((m.after - m.before) * 10) / 10;
  const up = delta > 0;
  return (
    <div className="mt-3 border border-line bg-paper/50 px-3 py-3 text-sm">
      <p className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
        Metric impact
      </p>
      <p className="mt-1 font-semibold text-ink">{m.metric}</p>
      <p className="mt-2 tabular-nums">
        <span className="text-ink-muted">{m.before_label || "before"}</span>{" "}
        <strong>{m.before}{m.unit || "%"}</strong>
        <span className="mx-2 text-ink-muted">→</span>
        <span className="text-ink-muted">{m.after_label || "after"}</span>{" "}
        <strong className="text-accent">{m.after}{m.unit || "%"}</strong>
        {delta !== 0 ? (
          <span className={`ml-2 font-semibold ${up ? "text-accent" : "text-warn"}`}>
            ({up ? "+" : ""}
            {delta}{m.unit || " pp"})
          </span>
        ) : null}
      </p>
      {m.source ? <p className="mt-1 text-xs text-ink-muted">Source: {m.source}</p> : null}
      {m.note ? <p className="mt-1 text-xs text-ink-muted">{m.note}</p> : null}
    </div>
  );
}

export function FailureAnalysis() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    fetchFailureCases()
      .then((d: Payload) => {
        setData(d);
        setActive(d.cases?.[0]?.id || null);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="font-display text-3xl font-semibold">Failure analysis</h1>
        <p className="mt-3 text-sm text-warn">{error}</p>
        <p className="mt-2 text-ink-muted">
          Start <code>contextiq-serve</code> or ensure{" "}
          <code>docs/eval-results/failure-cases.json</code> exists.
        </p>
      </div>
    );
  }

  if (!data) {
    return <div className="px-4 py-10 text-ink-muted">Loading failures…</div>;
  }

  const cases = data.cases || [];
  const selected = cases.find((c) => c.id === active) || cases[0];

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <header className="mb-8 border-b border-line pb-5">
        <p className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
          Evaluation
        </p>
        <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight">
          {data.title || "Failure analysis"}
        </h1>
        <p className="mt-2 text-ink-muted">
          {data.subtitle || "How ContextIQ fails — and what we measured after the fix."}
        </p>
        <p className="mt-2 text-xs text-ink-muted">
          {data.case_count ?? cases.length} cases · {data.mitigated_count ?? 0} mitigated ·{" "}
          {data.open_count ?? 0} open
        </p>
        <p className="mt-3">
          <Link href="/eval" className="text-sm font-semibold text-accent hover:underline">
            ← Evaluation workspace
          </Link>
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <nav className="space-y-1">
          {cases.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setActive(c.id)}
              className={`block w-full border px-3 py-2 text-left text-sm transition-colors ${
                selected?.id === c.id
                  ? "border-accent bg-accent-soft font-semibold text-ink"
                  : "border-line bg-paper-elev/50 text-ink-muted hover:border-accent"
              }`}
            >
              <span className="block text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
                {c.id}
                {c.status === "open" ? " · open" : " · mitigated"}
              </span>
              {c.title}
            </button>
          ))}
        </nav>

        {selected ? (
          <article className="border border-line bg-paper-elev/40 p-5">
            <div className="flex flex-wrap items-baseline gap-2">
              <h2 className="font-display text-xl font-semibold">{selected.title}</h2>
              <span className="text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
                {selected.failure_mode}
              </span>
            </div>

            <section className="mt-6">
              <h3 className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                Question
              </h3>
              <p className="mt-1 text-sm font-semibold leading-relaxed text-ink">
                {selected.question}
              </p>
              {selected.question_id ? (
                <p className="mt-1 text-xs text-ink-muted">Golden id: {selected.question_id}</p>
              ) : null}
            </section>

            {selected.retrieved?.length ? (
              <section className="mt-5">
                <h3 className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                  Retrieved (wrong / weak)
                </h3>
                <ul className="mt-2 space-y-1 text-sm">
                  {selected.retrieved.map((r) => (
                    <li key={r} className="font-mono text-xs text-ink">
                      {r}
                    </li>
                  ))}
                </ul>
                {selected.expected_sources?.length ? (
                  <p className="mt-2 text-xs text-ink-muted">
                    Expected: {selected.expected_sources.join(", ")}
                  </p>
                ) : null}
              </section>
            ) : null}

            <section className="mt-5 grid gap-4 sm:grid-cols-2">
              <div>
                <h3 className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                  Observed
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-ink">{selected.observed_behavior}</p>
              </div>
              <div>
                <h3 className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                  Expected
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-ink">{selected.expected_behavior}</p>
              </div>
            </section>

            {selected.fix ? (
              <section className="mt-5">
                <h3 className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                  Fix applied
                </h3>
                <p className="mt-1 text-sm">
                  <span className="font-semibold">{selected.fix.area}</span>
                  {selected.fix.summary ? ` — ${selected.fix.summary}` : null}
                </p>
              </section>
            ) : null}

            {selected.metric_impact ? <Impact m={selected.metric_impact} /> : null}

            {selected.lesson ? (
              <p className="mt-5 border-t border-line pt-4 text-sm italic text-ink-muted">
                {selected.lesson}
              </p>
            ) : null}
          </article>
        ) : (
          <p className="text-ink-muted">No cases yet.</p>
        )}
      </div>
    </div>
  );
}
