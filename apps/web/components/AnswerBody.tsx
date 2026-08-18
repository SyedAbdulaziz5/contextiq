"use client";

import type { ReactNode } from "react";
import type { Citation, FinalPayload } from "@/lib/types";
import { claimSpansForSource } from "@/lib/grounding";

type Props = {
  text: string;
  citations: Citation[];
  sources: FinalPayload["sources"];
  activeId: string | null;
  onSelect: (sourceId: string | null) => void;
};

function escapeRegExp(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Highlight claim spans for the active citation inside plain text segments. */
function highlightClaims(segment: string, claims: string[], keyPrefix: string): ReactNode[] {
  if (!claims.length || !segment) return [segment];
  const usable = claims.filter((c) => c.length >= 8 && segment.includes(c));
  if (!usable.length) {
    // try shorter / case-insensitive partial
    const lower = segment.toLowerCase();
    const partial = claims
      .map((c) => {
        const slice = c.slice(0, Math.min(48, c.length));
        const idx = lower.indexOf(slice.toLowerCase());
        return idx >= 0 ? segment.slice(idx, idx + slice.length) : null;
      })
      .filter((x): x is string => Boolean(x));
    if (!partial.length) return [segment];
    return highlightClaims(segment, partial, keyPrefix);
  }

  const pattern = new RegExp(`(${usable.map(escapeRegExp).join("|")})`, "g");
  const bits = segment.split(pattern);
  return bits.map((bit, i) => {
    if (usable.some((c) => c === bit)) {
      return (
        <mark
          key={`${keyPrefix}-h-${i}`}
          className="rounded-sm bg-accent-soft px-0.5 text-ink"
        >
          {bit}
        </mark>
      );
    }
    return <span key={`${keyPrefix}-t-${i}`}>{bit}</span>;
  });
}

export function AnswerBody({ text, citations, sources, activeId, onSelect }: Props) {
  const byNum = new Map<string, Citation>();
  for (const c of citations) {
    byNum.set(c.source_id.replace(/^S/i, ""), c);
  }
  for (const s of sources) {
    const num = s.source_id.replace(/^S/i, "");
    if (!byNum.has(num)) {
      byNum.set(num, {
        claim_span: "",
        source_id: s.source_id,
        title: s.title,
        section_title: s.section_title,
        source_url: s.source_url,
        snippet: s.snippet,
        chunk_key: s.chunk_key,
        doc_source_id: s.doc_source_id,
      });
    }
  }

  const activeClaims = activeId ? claimSpansForSource(citations, activeId) : [];
  const parts = text.split(/(\[\d+\])/g);

  return (
    <div className="whitespace-pre-wrap break-words leading-relaxed">
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        if (!m) {
          return (
            <span key={i}>{highlightClaims(part, activeClaims, `p${i}`)}</span>
          );
        }
        const num = m[1];
        const cite = byNum.get(num);
        const sid = cite?.source_id || `S${num}`;
        const active = activeId === sid;
        return (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(active ? null : sid)}
            aria-pressed={active}
            title={cite?.title || `Source ${num}`}
            className={`mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full border px-1.5 align-super text-[0.7rem] font-bold transition-colors ${
              active
                ? "border-accent bg-accent text-white"
                : "border-line bg-paper-elev text-accent hover:border-accent hover:bg-accent-soft"
            }`}
          >
            {num}
          </button>
        );
      })}
    </div>
  );
}
