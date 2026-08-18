import type { FinalPayload, TracePayload } from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8787";

/** Optional — only when API runs with CONTEXTIQ_AUTH_MODE=api_key (demo lock). */
const API_KEY = process.env.NEXT_PUBLIC_API_KEY?.trim() || "";

export { API_URL };

function apiHeaders(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { ...extra };
  if (API_KEY) {
    h["X-API-Key"] = API_KEY;
  }
  return h;
}

export type StreamHandlers = {
  onMeta?: (data: Record<string, unknown>) => void;
  onSources?: (data: { sources: unknown[] }) => void;
  onTrace?: (data: TracePayload) => void;
  onToken?: (text: string) => void;
  onFinal?: (data: FinalPayload) => void;
};

export async function checkHealth(signal?: AbortSignal): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, { signal });
    if (!res.ok) return false;
    const data = await res.json();
    return Boolean(data.ok);
  } catch {
    return false;
  }
}

export async function streamQuery(
  query: string,
  history: string[],
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/query/stream`, {
    method: "POST",
    headers: apiHeaders({
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    }),
    body: JSON.stringify({ query, history }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const lines = part.split("\n");
      let event = "message";
      const dataLines: string[] = [];
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (!dataLines.length) continue;
      const data = JSON.parse(dataLines.join("\n"));
      if (event === "meta") handlers.onMeta?.(data);
      else if (event === "sources") handlers.onSources?.(data);
      else if (event === "trace") handlers.onTrace?.(data as TracePayload);
      else if (event === "token") handlers.onToken?.(data.text || "");
      else if (event === "final") handlers.onFinal?.(data as FinalPayload);
    }
  }
}

export async function sendFeedback(traceId: string, feedback: "up" | "down") {
  const res = await fetch(`${API_URL}/feedback`, {
    method: "POST",
    headers: apiHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ trace_id: traceId, feedback }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchEvalDashboard() {
  const res = await fetch(`${API_URL}/eval/dashboard`, { headers: apiHeaders() });
  if (res.ok) return res.json();
  // fallback to static public file
  const local = await fetch("/eval/latest.json");
  if (!local.ok) throw new Error("No eval data");
  return local.json();
}

export async function fetchFailureCases() {
  const res = await fetch(`${API_URL}/eval/failures`, { headers: apiHeaders() });
  if (res.ok) return res.json();
  const local = await fetch("/eval/failures.json");
  if (!local.ok) throw new Error("No failure-analysis data");
  return local.json();
}

export async function fetchCostTradeoffs() {
  const res = await fetch(`${API_URL}/eval/cost-tradeoffs`, { headers: apiHeaders() });
  if (res.ok) return res.json();
  const local = await fetch("/eval/cost-tradeoffs.json");
  if (!local.ok) throw new Error("No cost-tradeoff data");
  return local.json();
}

export async function fetchTraceStats() {
  const res = await fetch(`${API_URL}/traces/stats`, { headers: apiHeaders() });
  if (!res.ok) throw new Error(`traces ${res.status}`);
  return res.json();
}

export async function fetchTraces(limit = 30) {
  const res = await fetch(`${API_URL}/traces?limit=${limit}`, { headers: apiHeaders() });
  if (!res.ok) throw new Error(`traces ${res.status}`);
  return res.json();
}
