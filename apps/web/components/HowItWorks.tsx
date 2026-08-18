"use client";

import { useEffect, useState } from "react";

const steps = [
  {
    title: "Ingest",
    body: "Structure-preserving parse of real docs — engineering, product, API, and support material.",
  },
  {
    title: "Hybrid retrieve",
    body: "Dense + sparse search fused with RRF, then reranked so keywords and meaning both count.",
  },
  {
    title: "Grounded answer",
    body: "Cited responses only. If retrieval confidence is weak, ContextIQ refuses instead of guessing.",
  },
  {
    title: "Evaluate",
    body: "Golden-set metrics and a CI gate so quality regressions fail the build — not the demo.",
  },
];

export function HowItWorks() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = window.setTimeout(() => setVisible(true), 80);
    return () => window.clearTimeout(t);
  }, []);

  return (
    <section className="mx-auto max-w-6xl px-4 py-16">
      <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
        How it works
      </h2>
      <p className="mt-2 max-w-xl text-ink-muted">
        One path from documents to a measured answer.
      </p>
      <ol className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step, i) => (
          <li
            key={step.title}
            className={`transition-all duration-500 ease-out ${
              visible ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0"
            }`}
            style={{ transitionDelay: `${120 + i * 90}ms` }}
          >
            <p className="text-[0.7rem] font-bold uppercase tracking-wider text-accent">
              {String(i + 1).padStart(2, "0")}
            </p>
            <h3 className="mt-2 text-base font-semibold text-ink">{step.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-muted">{step.body}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
