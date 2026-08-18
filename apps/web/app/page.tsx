import type { Metadata } from "next";
import Link from "next/link";
import { LandingHero } from "@/components/LandingHero";
import { HowItWorks } from "@/components/HowItWorks";

export const metadata: Metadata = {
  title: "ContextIQ — Knowledge & Support Intelligence",
  description:
    "Eval-first RAG platform for production knowledge and support systems. Hybrid retrieval, grounded citations, refusal, and a CI quality gate.",
};

export default function LandingPage() {
  return (
    <main>
      <LandingHero />
      <HowItWorks />
      <section className="border-t border-line/80 bg-paper-elev/40">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-14 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-xl">
            <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
              Measured quality, not vibes
            </h2>
            <p className="mt-2 text-ink-muted">
              Golden-set metrics, experiment compare, and a merge-blocking CI gate —
              so retrieval changes have a bar.
            </p>
          </div>
          <Link
            href="/eval"
            className="inline-flex shrink-0 items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            Open evaluation
          </Link>
        </div>
      </section>
    </main>
  );
}
