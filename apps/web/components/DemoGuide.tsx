"use client";

import Link from "next/link";
import { DEMO_STEPS, type DemoStepId } from "@/lib/demo";

type Props = {
  done: Set<DemoStepId>;
  active: DemoStepId;
  onDismiss: () => void;
  onFocusRetrieval: () => void;
  onMarkEval: () => void;
};

export function DemoGuide({ done, active, onDismiss, onFocusRetrieval, onMarkEval }: Props) {
  const completed = DEMO_STEPS.filter((s) => done.has(s.id)).length;

  return (
    <div className="mb-4 border border-accent/30 bg-accent-soft/60 px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[0.7rem] font-bold uppercase tracking-wider text-accent">
            60-second demo
          </p>
          <p className="mt-0.5 text-sm text-ink-muted">
            {completed}/{DEMO_STEPS.length} steps — follow the checklist
          </p>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="text-xs font-semibold text-ink-muted hover:text-ink"
        >
          Dismiss
        </button>
      </div>

      <ol className="mt-3 grid gap-2 sm:grid-cols-5">
        {DEMO_STEPS.map((step) => {
          const isDone = done.has(step.id);
          const isActive = active === step.id && !isDone;
          return (
            <li
              key={step.id}
              className={`border px-2.5 py-2 text-left transition-colors ${
                isDone
                  ? "border-accent/40 bg-paper-elev"
                  : isActive
                    ? "border-accent bg-paper-elev"
                    : "border-line/80 bg-paper/40"
              }`}
            >
              <p className="text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
                {isDone ? "Done" : `Step ${step.n}`}
              </p>
              <p className="mt-0.5 text-xs font-semibold text-ink">{step.title}</p>
              {isActive ? (
                <p className="mt-1 text-[0.7rem] leading-snug text-ink-muted">{step.hint}</p>
              ) : null}
              {step.id === "retrieval" && isActive ? (
                <button
                  type="button"
                  onClick={onFocusRetrieval}
                  className="mt-1.5 text-[0.7rem] font-semibold text-accent hover:underline"
                >
                  Highlight sources →
                </button>
              ) : null}
              {step.id === "evaluation" && !isDone ? (
                <Link
                  href="/eval"
                  onClick={onMarkEval}
                  className="mt-1.5 inline-block text-[0.7rem] font-semibold text-accent hover:underline"
                >
                  Open Eval →
                </Link>
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
