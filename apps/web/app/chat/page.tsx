import type { Metadata } from "next";
import { Suspense } from "react";
import { Chat } from "@/components/Chat";

export const metadata: Metadata = {
  title: "Demo — ContextIQ",
  description: "Ask grounded questions over the knowledge corpus with citations and refusal.",
};

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="px-4 py-10 text-ink-muted">Loading demo…</div>}>
      <Chat />
    </Suspense>
  );
}
