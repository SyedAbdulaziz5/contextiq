"use client";

import type { Citation, SourceRef } from "@/lib/types";

type Props = {
  sourceId: string;
  citations: Citation[];
  sources: SourceRef[];
  onClose: () => void;
};

export function CitationPanel({ sourceId, citations, sources, onClose }: Props) {
  const cite = citations.find((c) => c.source_id === sourceId);
  const src =
    sources.find((s) => s.source_id === sourceId) ||
    sources.find((s) => s.source_id.replace(/^S/i, "") === sourceId.replace(/^S/i, ""));

  const title = cite?.title || src?.title || "Source";
  const section = cite?.section_title || src?.section_title;
  const snippet = cite?.snippet || src?.snippet || "";
  const url = cite?.source_url || src?.source_url;
  const claim = cite?.claim_span;

  return (
    <aside className="mt-3 rounded-md border border-line bg-paper-elev p-4 animate-in fade-in">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[0.7rem] font-semibold uppercase tracking-wider text-ink-muted">
          Source
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-lg leading-none text-ink-muted hover:text-ink"
          aria-label="Close"
        >
          ×
        </button>
      </div>
      <h3 className="font-display text-lg font-semibold leading-snug">{title}</h3>
      {section ? <p className="mt-1 text-sm text-ink-muted">{section}</p> : null}
      {claim ? <p className="mt-2 text-sm text-ink-muted">Supports: “{claim}”</p> : null}
      {snippet ? (
        <blockquote className="mt-3 border-l-2 border-accent bg-accent-soft px-3 py-2 text-sm leading-relaxed">
          “{snippet}”
        </blockquote>
      ) : null}
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-block text-sm font-semibold text-accent hover:underline"
        >
          Open original →
        </a>
      ) : null}
    </aside>
  );
}
