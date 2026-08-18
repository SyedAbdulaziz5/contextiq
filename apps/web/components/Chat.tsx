"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { checkHealth, sendFeedback, streamQuery } from "@/lib/api";
import { DEMO_PRESETS, DEMO_STEPS, type DemoStepId } from "@/lib/demo";
import type { ChatMessage, SourceRef, TracePayload } from "@/lib/types";
import { AnswerBody } from "./AnswerBody";
import { CitationPanel } from "./CitationPanel";
import { DemoGuide } from "./DemoGuide";
import { GroundingPanel } from "./GroundingPanel";
import { RequestBreakdown } from "./RequestBreakdown";
import { RetrievalPath } from "./RetrievalPath";
import { SourcesPanel } from "./SourcesPanel";

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function nextActive(done: Set<DemoStepId>): DemoStepId {
  for (const s of DEMO_STEPS) {
    if (!done.has(s.id)) return s.id;
  }
  return "refusal";
}

export function Chat() {
  const searchParams = useSearchParams();
  const demoParam = searchParams.get("demo");
  const [demoMode, setDemoMode] = useState(demoParam === "1" || demoParam === "true");
  const [done, setDone] = useState<Set<DemoStepId>>(() => new Set());
  const [highlightRetrieval, setHighlightRetrieval] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState<boolean | null>(null);
  const [panelSources, setPanelSources] = useState<SourceRef[]>([]);
  const [lastTrace, setLastTrace] = useState<TracePayload | null>(null);
  const askingRef = useRef(false);

  const activeStep = useMemo(() => nextActive(done), [done]);

  const mark = useCallback((id: DemoStepId) => {
    setDone((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    const ping = () =>
      checkHealth().then((ok) => {
        if (!cancelled) setReady(ok);
      });
    ping();
    const id = setInterval(ping, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    if (demoParam === "1" || demoParam === "true") setDemoMode(true);
  }, [demoParam]);

  const ask = useCallback(
    async (qRaw: string) => {
      const q = qRaw.trim();
      if (!q || busy || askingRef.current) return;
      askingRef.current = true;
      mark("ask");

      setError(null);
      setInput("");
      const userMsg: ChatMessage = { id: uid(), role: "user", content: q };
      const asstId = uid();
      setMessages((m) => [
        ...m,
        userMsg,
        {
          id: asstId,
          role: "assistant",
          content: "",
          streaming: true,
          final: null,
          activeCitation: null,
        },
      ]);
      setBusy(true);

      const history = messages.filter((m) => m.role === "user").map((m) => m.content);

      try {
        await streamQuery(q, history, {
          onSources: (data) => {
            setPanelSources((data.sources || []) as SourceRef[]);
          },
          onTrace: (trace) => setLastTrace(trace),
          onToken: (text) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === asstId ? { ...m, content: m.content + text } : m)),
            );
          },
          onFinal: (data) => {
            setPanelSources(data.sources || []);
            if (data.trace) setLastTrace(data.trace);
            if (data.sources?.length) mark("retrieval");
            if (data.insufficient_context) {
              mark("refusal");
            } else {
              mark("answer");
            }
            setMessages((prev) =>
              prev.map((m) =>
                m.id === asstId
                  ? {
                      ...m,
                      content: data.display_answer || data.answer,
                      streaming: false,
                      final: data,
                    }
                  : m,
              ),
            );
          },
        });
      } catch (err) {
        setError((err as Error).message || "Request failed");
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstId
              ? {
                  ...m,
                  streaming: false,
                  content: m.content || "Could not reach the generation API.",
                }
              : m,
          ),
        );
      } finally {
        setBusy(false);
        askingRef.current = false;
      }
    },
    [busy, mark, messages],
  );

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await ask(input);
  }

  function setActiveCitation(msgId: string, sourceId: string | null) {
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, activeCitation: sourceId } : m)),
    );
  }

  async function onFeedback(msg: ChatMessage, fb: "up" | "down") {
    const tid = msg.final?.trace_id;
    if (!tid) return;
    try {
      await sendFeedback(tid, fb);
      setMessages((prev) =>
        prev.map((m) => (m.id === msg.id ? { ...m, feedback: fb } : m)),
      );
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function focusRetrieval() {
    mark("retrieval");
    setHighlightRetrieval(true);
    document.getElementById("retrieval-path")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    window.setTimeout(() => setHighlightRetrieval(false), 2200);
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      {demoMode ? (
        <DemoGuide
          done={done}
          active={activeStep}
          onDismiss={() => setDemoMode(false)}
          onFocusRetrieval={focusRetrieval}
          onMarkEval={() => mark("evaluation")}
        />
      ) : (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 text-sm">
          <p className="text-ink-muted">Ask anything in the knowledge corpus.</p>
          <button
            type="button"
            onClick={() => setDemoMode(true)}
            className="font-semibold text-accent hover:underline"
          >
            Start 60-second demo
          </button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <section className="flex min-h-[70vh] flex-col overflow-hidden border border-line bg-paper-elev">
          <header className="flex items-center justify-between border-b border-line px-4 py-3">
            <div>
              <h1 className="font-display text-xl font-semibold tracking-tight">Demo</h1>
              <p className="text-xs text-ink-muted">Knowledge &amp; support · grounded answers</p>
            </div>
            <div className="flex items-center gap-2 text-sm font-semibold">
              <span
                className={`inline-block h-2 w-2 rounded-full ${
                  ready ? "bg-accent" : ready === false ? "bg-warn" : "bg-line"
                }`}
              />
              <span className="text-ink-muted">
                {ready ? "Ready" : ready === false ? "Offline" : "…"}
              </span>
            </div>
          </header>

          <div className="flex-1 space-y-5 overflow-y-auto px-4 py-5">
            {messages.length === 0 ? (
              <div className="text-ink-muted">
                <p className="mb-3 text-sm">
                  {demoMode
                    ? "One click runs the query. Start with a grounded question, then try a refusal."
                    : "Ask a knowledge or support question. Try an unanswerable one to see refusal."}
                </p>
                <div className="grid gap-2">
                  {DEMO_PRESETS.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      disabled={busy}
                      onClick={() => ask(p.query)}
                      className="border border-line px-3 py-2.5 text-left transition-colors hover:border-accent hover:bg-accent-soft disabled:opacity-50"
                    >
                      <span className="block text-[0.65rem] font-bold uppercase tracking-wide text-ink-muted">
                        {p.label}
                      </span>
                      <span className="text-sm text-ink">{p.query}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m) => (
                <article key={m.id}>
                  <span className="mb-1 block text-[0.7rem] font-bold uppercase tracking-wider text-ink-muted">
                    {m.role === "user" ? "You" : "AI"}
                  </span>
                  {m.role === "assistant" && m.final ? (
                    <>
                      <AnswerBody
                        text={m.content}
                        citations={m.final.citations}
                        sources={m.final.sources}
                        activeId={m.activeCitation || null}
                        onSelect={(sid) => setActiveCitation(m.id, sid)}
                      />
                      <GroundingPanel
                        final={m.final}
                        onSelectSource={(sid) => setActiveCitation(m.id, sid)}
                      />
                      {m.final.trace_id ? (
                        <div className="mt-2 flex gap-1">
                          <button
                            type="button"
                            onClick={() => onFeedback(m, "up")}
                            className={`rounded border px-1.5 py-0.5 text-xs ${
                              m.feedback === "up"
                                ? "border-accent bg-accent-soft text-accent"
                                : "border-line text-ink-muted hover:border-accent"
                            }`}
                            aria-label="Thumbs up"
                          >
                            ▲
                          </button>
                          <button
                            type="button"
                            onClick={() => onFeedback(m, "down")}
                            className={`rounded border px-1.5 py-0.5 text-xs ${
                              m.feedback === "down"
                                ? "border-warn bg-warn-soft text-warn"
                                : "border-line text-ink-muted hover:border-warn"
                            }`}
                            aria-label="Thumbs down"
                          >
                            ▼
                          </button>
                        </div>
                      ) : null}
                      {m.activeCitation ? (
                        <CitationPanel
                          sourceId={m.activeCitation}
                          citations={m.final.citations}
                          sources={m.final.sources}
                          onClose={() => setActiveCitation(m.id, null)}
                        />
                      ) : null}
                    </>
                  ) : (
                    <p className="whitespace-pre-wrap">
                      {m.content}
                      {m.streaming ? (
                        <span className="ml-0.5 inline-block w-2 animate-pulse">▍</span>
                      ) : null}
                    </p>
                  )}
                </article>
              ))
            )}

            {messages.length > 0 && !busy ? (
              <div className="flex flex-wrap gap-2 border-t border-line pt-4">
                {DEMO_PRESETS.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => ask(p.query)}
                    className="border border-line px-2.5 py-1.5 text-xs font-semibold text-ink-muted hover:border-accent hover:text-ink"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <footer className="border-t border-line bg-paper-elev p-3">
            {error ? <p className="mb-2 text-sm text-warn">{error}</p> : null}
            <form className="flex gap-2" onSubmit={onSubmit}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question…"
                disabled={busy}
                className="min-h-11 flex-1 border border-line bg-paper px-3 text-ink outline-none focus:border-accent"
              />
              <button
                type="submit"
                disabled={busy || !input.trim()}
                className="bg-accent px-4 font-semibold text-white disabled:opacity-40"
                aria-label="Send"
              >
                ➤
              </button>
            </form>
          </footer>
        </section>

        <aside className="space-y-4">
          <RetrievalPath highlight={highlightRetrieval} />
          <div
            className={
              highlightRetrieval
                ? "rounded-sm ring-2 ring-accent ring-offset-2 ring-offset-paper"
                : undefined
            }
          >
            <SourcesPanel sources={panelSources} />
          </div>
          {lastTrace ? <RequestBreakdown trace={lastTrace} compact /> : null}
        </aside>
      </div>
    </div>
  );
}
