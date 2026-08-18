"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const githubUrl = process.env.NEXT_PUBLIC_GITHUB_URL?.trim() || "";

export function LandingHero() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <section className="relative overflow-hidden border-b border-line/80">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          backgroundImage:
            "linear-gradient(165deg, rgba(15,92,76,0.09) 0%, transparent 42%), radial-gradient(ellipse 80% 60% at 85% 20%, rgba(26,26,24,0.06), transparent)",
        }}
      />
      <div className="relative mx-auto grid max-w-6xl gap-12 px-4 pb-16 pt-14 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:pb-20 lg:pt-20">
        <div
          className={`transition-all duration-700 ease-out ${
            visible ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0"
          }`}
        >
          <p className="font-display text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            ContextIQ
          </p>
          <h1 className="mt-4 max-w-lg text-xl font-semibold leading-snug text-ink sm:text-2xl">
            Knowledge &amp; support answers you can trust — and measure.
          </h1>
          <p className="mt-3 max-w-md text-base text-ink-muted">
            Eval-first RAG platform for production knowledge and support systems.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/chat?demo=1"
              className="inline-flex items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
            >
              Try 60s demo
            </Link>
            <Link
              href="/architecture"
              className="inline-flex items-center justify-center rounded-md border border-line bg-paper-elev px-5 py-2.5 text-sm font-semibold text-ink transition-colors hover:border-accent hover:bg-accent-soft"
            >
              Architecture
            </Link>
            <Link
              href="/eval"
              className="inline-flex items-center justify-center rounded-md border border-line bg-paper-elev px-5 py-2.5 text-sm font-semibold text-ink transition-colors hover:border-accent hover:bg-accent-soft"
            >
              Evaluation
            </Link>
            {githubUrl ? (
              <a
                href={githubUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center rounded-md border border-line bg-paper-elev px-5 py-2.5 text-sm font-semibold text-ink transition-colors hover:border-accent hover:bg-accent-soft"
              >
                GitHub
              </a>
            ) : null}
          </div>
        </div>

        <div
          className={`transition-all delay-150 duration-700 ease-out ${
            visible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
          }`}
        >
          <PipelineVisual />
        </div>
      </div>
    </section>
  );
}

function PipelineVisual() {
  const stages = [
    "Docs",
    "Hybrid retrieve",
    "Rerank",
    "Grounded answer",
    "Eval gate",
  ];
  return (
    <div className="relative border border-line/80 bg-transparent p-6">
      <p className="mb-5 text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
        Pipeline
      </p>
      <ol className="space-y-0">
        {stages.map((label, i) => (
          <li key={label} className="flex gap-3">
            <div className="flex w-6 flex-col items-center">
              <span className="mt-1 h-2.5 w-2.5 rounded-full bg-accent" />
              {i < stages.length - 1 ? (
                <span className="my-1 w-px flex-1 bg-line" />
              ) : null}
            </div>
            <p
              className={`pb-5 text-sm font-semibold text-ink ${
                i === stages.length - 1 ? "pb-0" : ""
              }`}
            >
              {label}
            </p>
          </li>
        ))}
      </ol>
      <p className="mt-6 border-t border-line pt-4 text-sm text-ink-muted">
        Citations when grounded. Refusal when evidence is thin. Regression blocked in CI.
      </p>
    </div>
  );
}
