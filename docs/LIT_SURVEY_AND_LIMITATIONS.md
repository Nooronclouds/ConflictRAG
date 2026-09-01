# ConflictRAG — Literature Survey, Limitations & Future Work

> Viva reference for the team. Covers the core papers we built on (what they did,
> their limitations, what we took), the honest limitations of our system, the
> stretch goals, and future work. IEEE-style references at the end.

---

## 1. Literature Survey

### Core 1 — Lewis et al. (2020), *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (NeurIPS) — the RAG foundation
- **What it did:** Introduced RAG — a pretrained seq2seq **generator** (parametric memory) combined with a dense **vector index** (non-parametric memory) accessed by a neural retriever. Grounds generation in retrieved passages, giving provenance and updatable knowledge; achieved SOTA on knowledge-intensive tasks.
- **Limitations:** Assumes retrieved passages are mutually **consistent** — no mechanism for when sources contradict; can still blend/hallucinate; cloud-scale, not privacy-oriented.
- **What we took:** The core **retrieve-then-generate** architecture (MiniLM + ChromaDB retriever → Ollama generator). ConflictRAG = this pipeline **plus a Conflict-Aware Reasoning Layer (CARL) before generation.**

### Core 2 — Xu et al. (2024), *Knowledge Conflicts for LLMs: A Survey* (EMNLP) — our taxonomy
- **What it did:** Systematically categorizes knowledge conflicts into three types — **context-memory, inter-context, intra-memory** — and reviews their causes, LLM behaviors under conflict, and existing solutions.
- **Limitations:** A **survey** — descriptive only, no working system; the reviewed solutions are largely post-hoc or model-internal, with no pre-generation pipeline.
- **What we took:** The **conflict taxonomy** — we operationalize *inter-context* conflict as our **Factual / Temporal / Contradictory** classes, and adopt the framing that conflicts must be handled *explicitly*, not blended away.

### Core 3 — Wang et al. (2025), *Accommodate Knowledge Conflicts in Retrieval-augmented LLMs* (Swin-VIB) — conflict handling in RAG
- **What it did:** An information-theoretic analysis showing LLMs resolve confidently when conflicting vs. supplementary information differ **clearly**, but are uncertain when the difference is **ambiguous**. Proposes **Swin-VIB**, a variational information-bottleneck pipeline that adapts retrieved-information differences for robust generation.
- **Limitations:** Resolves the conflict **silently inside the model** (not surfaced to the user); heavy machinery; evaluated on multiple-choice **accuracy**, not auditable end-to-end; not privacy/self-hosted.
- **What we took:** The insight that conflict handling hinges on the **difference between sources** — but ConflictRAG **detects and *surfaces*** the conflict transparently (halt or resolve, with visible sources + a reasoning trace) rather than hiding the decision inside the model.

### Core 4 — Zhang et al. (2025), *FaithfulRAG: Fact-Level Conflict Modeling for Context-Faithful RAG* — claim-level conflict
- **What it did:** Shows that existing "faithful RAG" methods enforce context adherence by **suppressing the model's parametric knowledge**, which harms understanding. Proposes **FaithfulRAG**, which models discrepancies at the **fact level** and uses a self-thinking process to reason about conflicting knowledge.
- **Limitations:** Targets **parametric-vs-context** conflict (model memory vs. one retrieved context), **not inter-document** conflict between two retrieved sources; requires LLM self-reasoning (heavier); no explicit taxonomy or user-facing conflict UI.
- **What we took:** The **fact/claim-level** conflict-modeling idea — this validates our move to **claim-sentence-level detection** (vs. whole-chunk) and motivates our future claim-level work.

### Supporting papers
- **Yao et al. (2023), *ReAct: Synergizing Reasoning and Acting in Language Models* (ICLR).** *Did:* interleaves reasoning traces with tool actions so LLMs plan, act, and update. *Limitation:* needs capable LLMs + tools, latency, not conflict-specific. *We took:* the reasoning-trace idea → our **Agent-Trace panel**, and the (stretch) multi-hop + tool-verification design.
- **Es et al. (2023/2024), *RAGAS: Automated Evaluation of RAG*.** *Did:* reference-free RAG metrics (faithfulness, answer relevance, context precision/recall) via an LLM judge. *Limitation:* needs a strong (usually cloud) judge → costly, **breaks the privacy guarantee**, and is unreliable with small local models (we observed NaN / timeouts). *We took:* the **metric definitions**, but compute them **locally and deterministically** (NLI entailment for faithfulness; embedding cosine for relevance).
- **Huang et al. (2023), *A Survey on Hallucination in LLMs*.** *Did:* principles/taxonomy/challenges of hallucination. *We took:* problem motivation — why grounding + explicit conflict handling matter in high-stakes settings.

---

## 2. Current Limitations (state these honestly)

1. **Retrieval-bounded conflict detection** — CARL can only compare sources that retrieval surfaces; a conflicting passage buried in a **mixed-topic chunk** can fall below the relevance gate and be missed. *You can't reason about what you don't retrieve.*
2. **Over-firing on related corpora** — whole-document NLI can flag related documents as "conflicting"; mitigated by **rule-based** heuristics (claim-level comparison + concrete-cue requirement + citation filtering), not a learned model.
3. **Factual/entity-swap classification is weak (~34%)** — the rule-based classifier cannot separate ConflictBank entity-swap pairs that carry no surface number/date/negation cue.
4. **Rule-based reconciliation** — relies on year-difference and revision keywords; without those signals it can only *halt*, not resolve.
5. **Small local LLM (llama3.2:3b)** — limited answer quality; occasional hedging/hallucination; refusal detection is heuristic.
6. **NLI = DeBERTa-v3-base**, not the -large targeted in the report (chosen for speed/memory on a 6 GB GPU).
7. **Single-hop retrieval** — no multi-hop evidence chaining for complex questions.
8. **Inter-document conflicts only** — detects conflicts *between retrieved sources*, not between the model's parametric knowledge and the documents (FaithfulRAG's focus).
9. **Small end-to-end evaluation** — the controlled conflict benchmark is 5 planted cases; detection is measured on claim pairs, not large-scale document QA.
10. **Product scope** — local single-user, no authentication, no token streaming.

---

## 3. Stretch Goals (planned in the report, not built)

- Multi-hop agentic **ReAct** retrieval (OBJ1)
- External **tool verification** — web search / Python REPL / calculator (OBJ5)
- Token **streaming** in the chat UI
- **DeBERTa-v3-large** NLI for the final run

---

## 4. Future Work (each fixes a limitation above)

| Future build | Fixes limitation |
|---|---|
| **Claim-level conflict detection** (extract atomic claims, then compare) | 1, 2 |
| **Finer / topic-aware chunking + hybrid (dense + sparse) retrieval** | 1 |
| **Trained conflict-type classifier** (fine-tune on ConflictBank) | 3 |
| **Learned reconciliation** (source authority, recency, evidence quality) | 4 |
| **Parametric-vs-context conflict detection** (FaithfulRAG-style) | 8 |
| **Multi-hop + ReAct tool verification** | 7 + stretch |
| **Larger local LLM + DeBERTa-v3-large** | 5, 6 |
| **Larger end-to-end conflict benchmark + local RAGAS-style eval at scale** | 9 |

---

## 5. References (IEEE style)

[1] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W. Yih, T. Rocktäschel, S. Riedel, and D. Kiela, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Advances in Neural Information Processing Systems (NeurIPS)*, 2020.

[2] R. Xu, Z. Qi, Z. Guo, C. Wang, H. Wang, Y. Zhang, and W. Xu, "Knowledge conflicts for LLMs: A survey," in *Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP)*, 2024, pp. 8541–8565.

[3] J. Wang, Z. Xu, D. Jin, X. Yang, and T. Li, "Accommodate knowledge conflicts in retrieval-augmented LLMs: Towards robust response generation in the wild," arXiv:2504.12982, 2025.

[4] Q. Zhang, Z. Xiang, Y. Xiao, L. Wang, J. Li, X. Wang, and J. Su, "FaithfulRAG: Fact-level conflict modeling for context-faithful retrieval-augmented generation," arXiv:2506.08938, 2025.

[5] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, and Y. Cao, "ReAct: Synergizing reasoning and acting in language models," in *Proc. Int. Conf. Learning Representations (ICLR)*, 2023.

[6] S. Es, J. James, L. Espinosa-Anke, and S. Schockaert, "RAGAS: Automated evaluation of retrieval augmented generation," arXiv:2309.15217, 2023.

[7] L. Huang, W. Yu, W. Ma, W. Zhong, Z. Feng, H. Wang, Q. Chen, W. Peng, X. Feng, B. Qin, and T. Liu, "A survey on hallucination in large language models: Principles, taxonomy, challenges, and open questions," arXiv:2311.05232, 2023.

[8] P. He, X. Liu, J. Gao, and W. Chen, "DeBERTa: Decoding-enhanced BERT with disentangled attention," in *Proc. Int. Conf. Learning Representations (ICLR)*, 2021.

[9] N. Reimers and I. Gurevych, "Sentence-BERT: Sentence embeddings using Siamese BERT-networks," in *Proc. EMNLP-IJCNLP*, 2019.

[10] Z. Su, J. Zhang, X. Qu, T. Zhu, Y. Li, J. Sun, J. Li, M. Zhang, and Y. Cheng, "ConflictBank: A benchmark for evaluating the influence of knowledge conflicts in LLMs," in *Advances in Neural Information Processing Systems (NeurIPS)*, 2024.

### Additional surveys reviewed
[11] A. Singh, A. Ehtesham, S. Kumar, and T. T. Khoei, "Agentic retrieval-augmented generation: A survey on agentic RAG," arXiv:2501.09136, 2025.

[12] Y. Li, X. Fu, G. Verma, P. Buitelaar, and M. Liu, "Mitigating hallucination in large language models (LLMs): An application-oriented survey on RAG, reasoning, and agentic systems," arXiv:2510.24476, 2025.

[13] J. Liang, G. Su, H. Lin, Y. Wu, R. Zhao, and Z. Li, "Reasoning RAG via System 1 or System 2: A survey on reasoning agentic retrieval-augmented generation for industry challenges," arXiv:2506.10408, 2025.
