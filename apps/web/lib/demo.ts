export const DEMO_ANSWERABLE =
  "What is the maximum execution timeout for an AWS Lambda function?";

export const DEMO_REFUSE = "What is the current stock price of Amazon?";

export const DEMO_PRESETS = [
  {
    id: "grounded",
    label: "Grounded answer",
    query: DEMO_ANSWERABLE,
    kind: "answerable" as const,
  },
  {
    id: "nextjs",
    label: "Another grounded",
    query: "How do Next.js Server Components work?",
    kind: "answerable" as const,
  },
  {
    id: "refuse",
    label: "Should refuse",
    query: DEMO_REFUSE,
    kind: "unanswerable" as const,
  },
] as const;

export type DemoStepId =
  | "ask"
  | "answer"
  | "retrieval"
  | "evaluation"
  | "refusal";

export const DEMO_STEPS: {
  id: DemoStepId;
  n: number;
  title: string;
  hint: string;
}[] = [
  {
    id: "ask",
    n: 1,
    title: "Ask a question",
    hint: "Use a preset below — one click sends it.",
  },
  {
    id: "answer",
    n: 2,
    title: "Answer + citations",
    hint: "Grounded answers cite sources in the text.",
  },
  {
    id: "retrieval",
    n: 3,
    title: "View retrieval",
    hint: "Dense → sparse → RRF → rerank in the sources panel.",
  },
  {
    id: "evaluation",
    n: 4,
    title: "Open Evaluation",
    hint: "See metrics and experiments.",
  },
  {
    id: "refusal",
    n: 5,
    title: "See a refusal",
    hint: "Ask the stock-price preset — out of corpus.",
  },
];
