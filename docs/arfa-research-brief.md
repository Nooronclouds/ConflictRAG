# Arfa — Research & Paper Brief (ConflictRAG)

## Your mission
Own the paper's **Related Work + Evaluation + Results**. Two things you can start now
(neither blocked by the system):
1. Write the **Related Work** section from the reading list below.
2. Learn **RAGAS** on a toy example, ready for the Phase-5 evaluation.

## The paper's argument (so you know where each paper goes)
1. RAG grounds LLMs in documents — but hallucination persists.
2. A big cause is **knowledge conflict**: sources disagree, and standard RAG hides it.
3. Existing fixes are **post-hoc** (after generation) or lack a **taxonomy-driven,
   pre-generation** reconciliation — and are **cloud-only**.
4. **Gap → ConflictRAG:** pre-generation detection + classify + reconcile/halt/present,
   transparent, over a **private self-hostable** knowledge base.

## Reading list (you have the first 10; download the rest)

### A. Foundations — RAG & retrieval
- Lewis et al. 2020, RAG (NeurIPS)   ✅ have
- Karpukhin et al. 2020, Dense Passage Retrieval (DPR)   ← get
- Guu et al. 2020, REALM   ← get

### B. The problem — hallucination & knowledge conflict
- Huang et al. 2023, Hallucination survey   ✅ have
- Xu et al. 2024, Knowledge Conflicts for LLMs: A Survey (EMNLP)   ✅ have
- Xie et al. 2024, "Adaptive Chameleon or Stubborn Sloth" — ConflictQA (ICLR)   ← get
- Niu et al. 2024, RAGTruth — RAG hallucination benchmark (ACL)   ← get

### C. Closest solution works — position AGAINST these ("close, but not CARL")
- Asai et al. 2023, Self-RAG — self-reflection/critique, but NO conflict taxonomy   ← get
- Yan et al. 2024, CRAG (Corrective RAG) — fixes bad retrieval, NOT conflict detection   ← get
- Zhang et al. 2025, FaithfulRAG — fact-level conflict, but no agentic reconcile + cloud   ✅ have
- Wang et al. 2025, Accommodate Knowledge Conflicts — via fine-tuning, not pre-generation   ✅ have

### D. Detection foundations — NLI / fact verification
- Thorne et al. 2018, FEVER — fact verification with evidence (NLI-for-checking)   ← get
- He et al. 2021/2023, DeBERTaV3 — the NLI model we use   ← get
- Manakul et al. 2023, SelfCheckGPT — hallucination detection via consistency (post-hoc)   ← get

### E. Benchmarks & evaluation
- Su et al. 2024, ConflictBank — the conflict benchmark we use (NeurIPS)   ← get
- Wu et al. 2024, ClashEval — internal-vs-context conflict (NeurIPS)   ← get
- Es et al. 2023, RAGAS — evaluation framework   ✅ have

### F. Prior-art TOOLS (the "answer + supporting/contradicting sources" UX — cite to differentiate)
- Nicholson et al. 2021, scite: smart citations (supporting/contradicting/mentioning)   ← get
- Tools to mention: Consensus, Elicit, Google NotebookLM

## The key framing (write this into Related Work)
Detection uses off-the-shelf NLI — not our novelty. Tools like scite/Consensus already
show supporting vs contradicting sources — also not our novelty. **Our contribution is the
composition:** pre-generation, taxonomy-driven reconcile/halt/present, transparent, over a
private self-hostable KB, with a measured trust improvement. Every "closest work" above is
either post-hoc, cloud-only, or lacks the reconcile step — that's the gap we fill.

## How to find more
Google Scholar / arXiv / Semantic Scholar. Keywords: "knowledge conflict RAG",
"pre-generation conflict detection", "faithful retrieval-augmented generation",
"conflicting evidence LLM", "citation stance classification". For each new paper, note:
what problem, what method, and *why it stops short of CARL*.
Verify every citation's exact author/year/venue before it goes in the paper.