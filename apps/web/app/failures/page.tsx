import type { Metadata } from "next";
import { FailureAnalysis } from "@/components/FailureAnalysis";

export const metadata: Metadata = {
  title: "Failures — ContextIQ",
  description: "Curated RAG failure cases with measured fixes from the golden set.",
};

export default function FailuresPage() {
  return <FailureAnalysis />;
}
