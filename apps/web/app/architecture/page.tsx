import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Architecture — ContextIQ",
  description:
    "Hybrid retrieval, grounded generation, evaluation, and CI — how ContextIQ is built.",
};

const decisions = [
  {
    title: "Eval before retrieval",
    body: "A golden set defines quality before features ship. CI fails merges that regress metrics.",
  },
  {
    title: "Hybrid, not vectors alone",
    body: "Dense embeddings miss exact IDs and error strings. Sparse + dense → RRF → rerank closes that gap.",
  },
  {
    title: "Refuse when ungrounded",
    body: "Insufficient evidence is a first-class outcome — better than a confident wrong answer.",
  },
  {
    title: "Free local defaults",
    body: "sentence-transformers + Ollama (extractive fallback). Cloud providers stay optional behind the same interfaces.",
  },
];

export default function ArchitecturePage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <p className="text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
        Architecture
      </p>
      <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight text-ink">
        How ContextIQ is built
      </h1>
      <p className="mt-3 text-ink-muted">
        Production-minded RAG for knowledge and support — not a chat wrapper.
      </p>

      <ol className="mt-10 space-y-0 border-l border-line pl-6">
        {[
          "Ingest & structural chunk",
          "Embed (BGE-small)",
          "Query route / rewrite",
          "Dense + sparse retrieve",
          "RRF fuse → rerank",
          "Grounded generate + cite",
          "Refuse if weak evidence",
          "Trace · feedback · eval · CI gate",
        ].map((label, i) => (
          <li key={label} className="relative pb-5 last:pb-0">
            <span className="absolute -left-[1.55rem] top-1.5 h-2.5 w-2.5 rounded-full bg-accent" />
            <p className="text-sm font-semibold text-ink">
              <span className="mr-2 text-ink-muted">{i + 1}.</span>
              {label}
            </p>
          </li>
        ))}
      </ol>

      <h2 className="mt-14 font-display text-xl font-semibold text-ink">Decisions that matter</h2>
      <ul className="mt-6 space-y-6">
        {decisions.map((d) => (
          <li key={d.title}>
            <h3 className="text-sm font-semibold text-ink">{d.title}</h3>
            <p className="mt-1 text-sm leading-relaxed text-ink-muted">{d.body}</p>
          </li>
        ))}
      </ul>

      <p className="mt-12 text-sm text-ink-muted">
        Full write-up in the repo:{" "}
        <code className="rounded bg-accent-soft px-1.5 py-0.5 text-accent">docs/architecture.md</code>
      </p>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/chat?demo=1"
          className="inline-flex rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
        >
          Try 60s demo
        </Link>
        <Link
          href="/eval"
          className="inline-flex rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink hover:border-accent hover:bg-accent-soft"
        >
          Evaluation
        </Link>
      </div>
    </main>
  );
}
