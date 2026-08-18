# RAG Concepts — What You Must Actually Understand

This is not a glossary to skim. It is the mental model behind ContextIQ. If you can explain every section out loud without the file open, you are ready to defend this project in interviews.

---

## 1. What RAG is (and is not)

**Retrieval-Augmented Generation** = at answer time, fetch relevant text from a knowledge store, put it in the prompt, and ask the LLM to answer *from that text*.

```
User question
    → Retrieve relevant chunks from your corpus
    → Stuff those chunks into the LLM context
    → Generate an answer grounded in those chunks
```

**RAG is not:**
- Fine-tuning the model on your docs (different cost, different failure modes)
- Letting the model answer from parametric memory alone (hallucination risk on private/current docs)
- "Vector database + chatbot" as a product category — that is a *implementation*, not the idea

**Why RAG exists:** LLMs are strong at language and weak at *your* facts, especially after their training cutoff, for private corpora, or for exact quotas/IDs. Retrieval injects the right facts at runtime.

---

## 2. The pipeline, piece by piece

### 2.1 Ingestion & parsing
Raw PDFs/HTML/MD → structured text. Tables and headings matter. If you flatten a quota table into a bag of words, retrieval and citation quality die early.

### 2.2 Chunking
Split documents into pieces small enough to embed and retrieve, large enough to keep meaning.

| Strategy | Idea | Failure mode |
|---|---|---|
| Fixed-size | N tokens + overlap | Cuts mid-sentence / mid-table |
| Structural | Split on headings → paragraphs | Uneven sizes; needs good parsers |
| Semantic | Split where topic similarity drops | Costly; can still miss structure |

**Interview line:** "Chunking is a retrieval hyperparameter. I measure Context Recall per strategy instead of picking 500/50 from a blog."

### 2.3 Embeddings
A model maps text → a dense vector so "max timeout" and "maximum execution duration" land near each other in vector space.

ContextIQ plans **Amazon Titan Text Embeddings V2** (`amazon.titan-embed-text-v2:0`): up to 8,192 tokens in, default **1024-dim** vectors (also 512 / 256).

**Limitation of dense-only search:** exact tokens (model IDs, error codes like `429`, function names) can lose to paraphrases. That is why we add keyword search.

### 2.4 Hybrid retrieval
1. **Dense:** cosine similarity on embeddings → top-k  
2. **Sparse:** Postgres `tsvector` / `ts_rank` (BM25-like) → top-k  
3. **Fusion:** Reciprocal Rank Fusion (RRF)

```
RRF_score(d) = Σ  1 / (k + rank_i(d))    for each ranked list i, typically k = 60
```

RRF cares about *rank positions*, not incompatible raw scores — which is why it is the default fusion for hybrid search.

### 2.5 Reranking
After fusion you still have ~20–30 candidates. A **cross-encoder** (query + chunk scored together) reorders them and you keep top 5–8 for the prompt. This is often the largest single quality jump after hybrid search, and tutorials usually skip it.

### 2.6 Generation + citations
Prompt: answer *only* from provided chunks; cite `[S1]`, `[S2]`; if evidence is weak, refuse.

Structured output beats hope-based markdown:

```json
{
  "answer": "...",
  "citations": [{"claim_span": "...", "source_id": "S2"}],
  "confidence": "high",
  "insufficient_context": false
}
```

### 2.7 Evaluation
Without metrics you are debugging by vibe. With a golden set you can say: "Structural chunking raised Context Recall from 0.72 → 0.86 on the same questions."

---

## 3. Failure modes you must name

| Failure | Symptom | Typical fix |
|---|---|---|
| **Missed retrieval** | Right doc never in top-k | Better chunking, hybrid, query rewrite, HyDE |
| **Noisy retrieval** | Top-k full of irrelevant chunks | Rerank, metadata filters, raise relevance threshold |
| **Hallucination** | Fluent answer not in context | Grounding prompt, refusal, faithfulness check |
| **Citation lie** | Cites S3 but claim came from nowhere | Structured citations + verify claim⊂chunk |
| **Wrong refusal** | Knew the answer but refused | Threshold tuning; measure refusal accuracy |
| **Overconfident wrong** | Answered unanswerable questions | Explicit unanswerable golden subset |
| **Lost table facts** | Quotas wrong | Preserve table structure in parse/chunk |

---

## 4. Metrics (what "good" means)

| Metric | Question it answers |
|---|---|
| **Context Recall** | Did we retrieve the chunks that contain the answer? |
| **Context Precision** | Of what we retrieved, how much was actually useful? |
| **Faithfulness** | Are claims supported by the retrieved context? |
| **Answer Relevancy** | Did we address the question asked? |
| **Refusal Accuracy** | Do we refuse when (and only when) we should? |

**Context Recall** is the Phase 0–4 north star: if the right source never enters the prompt, generation cannot honestly succeed.

Golden format:

```json
{
  "id": "q042",
  "question": "...",
  "expected_answer": "...",
  "expected_source_ids": ["aws-lambda-limits"],
  "category": "factual",
  "notes": "optional"
}
```

`expected_source_ids` must match `corpus/sources.json` → later `documents.source_id`.

---

## 5. Why eval-first (Phase 0)

Most portfolios:

1. Wire LangChain + Pinecone  
2. Demo a happy-path question  
3. Never measure regression  

ContextIQ:

1. Lock corpus + source IDs  
2. Write 50–100 labeled questions across hard categories  
3. Only then implement retrieval  
4. Every change produces a number  

That sequence is the portfolio differentiator. Recruiters have seen the chatbot. They have not often seen a golden set and a CI quality gate.

---

## 6. Query understanding (later phases, know the words)

- **Query rewrite:** turn chatty / multi-turn questions into a standalone retrieval query  
- **HyDE:** generate a hypothetical answer, embed *that*, retrieve — sometimes better for complex questions; always A/B on the golden set  
- **Routing:** "hi" should not hit the vector index  

---

## 7. Guardrails (later, but design for them now)

- Retrieved text is **untrusted data**, not instructions (prompt injection)  
- Second-pass "does context support this claim?" for faithfulness sampling  
- Auth + rate limits so a public demo does not burn Bedrock budget  

---

## 8. One paragraph you should memorize

> RAG fetches relevant document chunks and conditions the LLM on them so answers stay grounded. Quality lives or dies on retrieval: hybrid search fixes pure-vector blind spots on exact keywords; reranking cleans the final context; citations and refusal stop confident lies. None of that is real until you measure Context Recall, Faithfulness, and Refusal Accuracy on a golden set you built before you wrote retrieval code.

---

## Further reading (when you implement)

- Reciprocal Rank Fusion (Cormack et al.)  
- RAGAS metrics / claim-level faithfulness  
- AWS docs pages listed in `corpus/sources.json` — your ground truth  
- Project guide: `RAG_project_guide.txt`
