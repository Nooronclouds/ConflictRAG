# ConflictRAG — Project Status & PRD (hand-off document)

> Give this file to any AI assistant (or teammate) to get fully up to speed on the project:
> what it is, how it's built, what's measured, what's left, and how to help write the paper.
> Last updated: 2026-08-20. Deadline: ~2026-08-26 (finishing ASAP).

---

## 1. What ConflictRAG is (in one paragraph)

ConflictRAG is a **fully local, open-source, self-hostable document question-answering system** for
high-stakes, confidential work (legal, healthcare, finance). Unlike normal RAG (and cloud tools like
Google NotebookLM), when two documents disagree it does **not** silently pick one — it **detects the
conflict before generating**, classifies it, and either resolves it transparently (if one source is a
dated revision of another) or halts and asks the user. It also refuses to answer when the corpus has no
source ("not found"). Because everything runs on-premise (local LLM, local models), no document ever
leaves the user's machine. The product persona is a trustworthy "Librarian."

## 2. Differentiators (the novelty, honestly framed)

- **vs NotebookLM / Perplexity / ChatPDF:** they ground + cite but treat sources as consistent, and are
  cloud-only. ConflictRAG detects/reconciles conflicts and runs fully private/local.
- **vs scite.ai / Consensus:** they surface supporting/contradicting *citations*, but post-hoc, over a
  fixed scientific-paper corpus, in the cloud. ConflictRAG does **pre-generation** conflict handling over
  the user's **own private KB**.
- **vs open-source RAG (Danswer/Onyx, Kotaemon, PrivateGPT):** they self-host but do **no** conflict reasoning.
- **The novelty is the SYSTEM COMPOSITION** (pre-generation conflict detection + taxonomy + reconciliation +
  private/self-hostable), NOT the individual models. The detection model (NLI) is off-the-shelf. State this
  honestly in the paper — naming the components is integrity, not weakness. Enough for an IEEE/Scopus student
  conference; not a novel-algorithm claim for a top ML venue.

## 3. Architecture (all models used at INFERENCE — nothing is trained)

```
Question
  -> Retrieve         (sentence-transformers MiniLM embeddings + ChromaDB)   [pretrained, inference]
  -> CARL:
       detect         (DeBERTa-v3-base NLI, MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli)  [pretrained]
       classify       (rule-based: negation/year/number -> factual|temporal|contradictory)
       reconcile      (recency/revision words -> resolvable? governing vs superseded)
  -> Decide one of 4 response types, + related-sources reading list
  -> Generate         (Ollama, llama3.2:3b)  [pretrained, inference]  (only for confident/resolved)
```

The **evaluation dataset** is used only to MEASURE the system (precision/recall), never to train it.

**Stack:** Python 3.11 (venv), torch 2.6.0+cu124 (GPU), FastAPI, ChromaDB, sentence-transformers,
transformers/DeBERTa, Ollama (llama3.2:3b), React frontend. Dev GPU = RTX 3050 6GB (Noor); Meiraj has RTX 4050.

## 4. The four response types (product behavior)

1. **confident** — answer + citations + related_sources
2. **resolved** — a revision: answer with the current value + a struck-through "superseded" note + related_sources
3. **conflict** — genuine clash, halts and shows both sources side by side + related_sources
4. **not_found** — honest refusal when the KB has nothing + related_sources
   (API shapes are in `docs/api-contract.md`.)

## 5. What is BUILT and verified (DONE)

**Backend (`backend/app/`):**
- `config.py` settings; `store.py` ChromaDB + embeddings; `ingest.py` PDF + text ingest;
  `retrieve.py`; `generate.py` (Ollama, baseline/conflictrag prompt modes);
  `nli.py` (DeBERTa check_pair); `conflict.py` (detect_conflicts / classify_conflict / reconcile);
  `pipeline.py` (`answer_question`, 4 types + related_sources, `mode` toggle);
  `main.py` (FastAPI: `/ask`, `/ingest` async w/ in-memory status registry, `/documents`).
- Demos proven: "travel allowance" -> resolved (₹250 supersedes ₹500); "office capacity 200 vs 350" -> conflict halt.

**Evaluation dataset (`dataset/eval_dataset.jsonl`, 795 rows):**
- ConflictBank subset 300 (default-claim vs conflict-claim pairs, typed) + planted 95 + negatives 400.
- Balanced ~395 conflict / 400 no_conflict; 55% hard negatives.
- Schema per row: `{original, conflicting, conflict_type, label, source, subtype}`.
- Built by `dataset/merge_and_verify.py`.

**Frontend (`frontend/mockups/`):** 4 static HTML mockups (KEPT as the design): not-found, resolved,
conflict, confident. Scholarly "reading room" aesthetic, Fraunces serif for the Librarian voice.

## 6. Measured RESULTS (the paper's numbers)

**Conflict DETECTION** (NLI, `run_eval.py`, at threshold 0.6):
- **precision 0.959, recall 0.937, F1 0.948, accuracy 0.948** — exceeds the FR2 target (>0.85).
- Recall by type: factual 97.4%, temporal 88.6%, contradictory 93.8%.
- False-alarm rate on negatives: paraphrase 2.5%, same_domain 3.3% (hard), unrelated 5.0%.
- Threshold sweep available (0.5->0.9); precision rises to 0.974 at 0.9 with recall 0.853.

**Conflict-type CLASSIFICATION** (rule-based, `run_classify_eval.py`):
- **72.4% overall.** By source: planted **100%**, ConflictBank **63.7%**.
- By type: contradictory 100%, temporal 92.1%, factual 34.2%.
- Honest limitation: ConflictBank "misinformation->factual" pairs are entity swaps with no surface
  number/date/negation cue, so they misclassify. Documented as a limitation; a trained classifier is future work.
  (An LLM classifier via the 3B model was tried and did WORSE — dropped.)

## 7. What is LEFT to build (by area, priority order)

**Backend (Noor):**
- [ ] **RAGAS evaluation** (Phase 5): faithfulness / answer-relevance / context-precision-recall,
      baseline (mode="baseline") vs conflictrag, on the full answer pipeline. THIS is the remaining paper number.
- [ ] **Data storage / folders**: replace the in-memory `DOCUMENTS` registry with a persistent store
      (e.g. SQLite) so document status + a real folder structure survive restarts (the KB folder-explorer the FE wants).
- [ ] **Agent-trace emission**: have the pipeline record each step (retrieve -> detect -> classify -> reconcile ->
      generate) and expose it in the `/ask` response so the frontend Trace UI can render it.
- [ ] (stretch, "full CARL" per proposal) multi-hop retrieval; ReAct tool verification (web/calc/python); token streaming.
- [ ] Docker packaging (Phase 6) for one-command self-hosting.
- Backlog quality items (see `BACKLOG.md`): citations = used-not-retrieved; drop low-relevance related_sources;
      sentence-level conflict detection; prune NLI pairs for speed.

**Frontend (Chetan):**
- [ ] Turn the 4 static mockups into a real **React (Vite + TS)** app, components per screen.
- [ ] Wire to the API (`docs/api-contract.md`) through ONE `src/api.ts` module (mock now, real fetch later).
- [ ] Render all 4 response types from `/ask` + the `related_sources` reading list.
- [ ] Functional **upload** + poll `/documents` until status `ready`.
- [ ] **Agent-Trace UI** (NEW — not in the mockups): collapsible panel showing the reasoning steps.
- [ ] Attach / paperclip flow ("ask about this document + KB").
- [ ] (optional) make the KB a Windows-folder-explorer look.

**Paper (Arfa + Noor):** related work (cite scite/Consensus/NotebookLM + the 26 refs in the proposal),
method (CARL), results (Section 6 numbers), honest limitations (classification on ConflictBank), future work.

## 8. Team & roles

- **Noor** (lead/architect): backend + CARL + integration. RTX 3050 6GB.
- **Meiraj**: dataset (planted + negatives) + backend #2. RTX 4050 (runs heavy models).
- **Arfa**: ConflictBank sourcing + evaluation + paper writing. No GPU.
- **Chetan**: frontend. AMD GPU (never runs the backend; calls the API).

## 9. How to run (dev)

```
# backend
cd conflictRAG/backend
py -3.11 -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
ollama pull llama3.2:3b
uvicorn app.main:app --reload --port 8000     # Swagger at http://localhost:8000/docs

# evaluation
python run_eval.py            # detection precision/recall
python run_classify_eval.py   # classification accuracy
```

## 10. Key facts to not get wrong

- ConflictRAG is candora's successor idea done properly. Candora was a finance-scoped hackathon prototype.
- CARL = Conflict-Aware Reasoning **Layer** (R = Reasoning). Reconciliation is a step *inside* the reasoning.
- The privacy claim REQUIRES the LLM to be local (Ollama), never a cloud API — this is core, not optional.
- Detection is excellent (96%); classification is the weak secondary metric (72%, documented). Don't over-claim.
