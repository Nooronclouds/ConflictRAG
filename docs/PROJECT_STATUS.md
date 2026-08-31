# ConflictRAG — Project Status & PRD (hand-off document)

> Give this file to any AI assistant (or teammate) to get fully up to speed on the project:
> what it is, how it's built, what's measured, what's left, and how to help write the paper.
> Last updated: 2026-08-29. Deadline: ~2026-08-26 (finishing ASAP — past nominal deadline, wrapping up).

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
  `pipeline.py` (`answer_question`, 4 types + related_sources, `mode` toggle, **relevance gate**);
  `db.py` (**SQLite** — folders, documents, conversations, messages; hand-written, no seed data);
  `main.py` (FastAPI — full endpoint list below).
- Demos proven: "travel allowance" -> resolved (₹250 supersedes ₹500); "office capacity 200 vs 350" -> conflict halt.

**API endpoints (`main.py`), all wired to the live React app:**
- `GET /folders`, `POST /folders`, `DELETE /folders/{id}` (moves its docs back to root)
- `GET /documents`, `GET /documents/view?name=` (serves the raw PDF), `DELETE /documents?name=` (removes chunks from Chroma **and** the metadata row)
- `POST /ingest` (writes to BOTH Chroma via `ingest_pdf` AND SQLite via `db.add_document`)
- `POST /ask` (stores the full response as JSON so a chat can be reopened without re-running)
- `GET /conversations`, `GET /conversations/{cid}` (loads a saved chat)

**Data model — two stores, on purpose:** ChromaDB holds the big data (vectors + chunk text); SQLite
holds only small metadata (folder tree, doc list, chat history). SQLite is the right choice *because*
the heavy data never lives in it — Postgres is the documented future path for multi-tenant scale, isolated
to `db.py`/`store.py`.

**Evaluation dataset (`dataset/eval_dataset.jsonl`, 795 rows):**
- ConflictBank subset 300 (default-claim vs conflict-claim pairs, typed) + planted 95 + negatives 400.
- Balanced ~395 conflict / 400 no_conflict; 55% hard negatives.
- Schema per row: `{original, conflicting, conflict_type, label, source, subtype}`.
- Built by `dataset/merge_and_verify.py`.

**Frontend (`frontend/`, React 18 + Vite + TypeScript) — BUILT and wired live to the backend:**
- Windows-11 File-Explorer glass aesthetic (Fraunces serif for the Librarian voice). 3-pane layout:
  left folder tree, context-sensitive middle pane, right Librarian chat.
- `src/api.ts` is the single data layer (real `fetch` to `http://localhost:8000`).
- All 4 response types render; chat history persists and reopens saved chats (no duplicate); New-folder
  in-app modal; **click a file to preview the PDF; hover to delete a file or folder (with confirm);
  upload shows a "Processing…" banner** while each PDF is read/chunked/embedded.
- The 4 original static mockups were superseded; `frontend/mockups/conflictrag-ui.html` kept as the
  reference wireframe. NOTE: the frontend is Chetan's contribution to push — it is git-excluded from Noor's repo.

## 6. Measured RESULTS (the paper's numbers)

**Conflict DETECTION** (NLI, `run_eval.py`, at threshold 0.6):
- **precision 0.959, recall 0.937, F1 0.948, accuracy 0.948** — exceeds the FR2 target (>0.85).
- Recall by type: factual 97.4%, temporal 88.6%, contradictory 93.8%.
- False-alarm rate on negatives: paraphrase 2.5%, same_domain 3.3% (hard), unrelated 5.0%.
- Threshold sweep available (0.5->0.9); precision rises to 0.974 at 0.9 with recall 0.853.

**Conflict-type CLASSIFICATION** (rule-based, `run_eval.py`):
- **74.7% overall** (295/395). By type: contradictory **100%**, temporal **100%**, factual 34.2%.
- (Improved from 72.4% on 2026-08-31: years are no longer counted as "factual" numbers,
  so temporal went 92.1% -> 100%.)
- Honest limitation: ConflictBank "misinformation->factual" pairs are entity swaps with no surface
  number/date/negation cue, so they misclassify. Documented as a limitation; a trained classifier is future work.
  (An LLM classifier via the 3B model was tried and did WORSE — dropped.)

## 6c. End-to-end conflict-handling eval (2026-08-31, `run_conflict_eval.py`)

Controlled benchmark: the script ingests its OWN planted-conflict corpus into a
separate collection (`conflictrag_eval`), so it needs no pre-existing KB and is fully
reproducible. 5 planted conflicts (factual/temporal/contradictory) + 5 consistent
questions, baseline RAG vs ConflictRAG.

| metric | baseline | ConflictRAG |
|---|---|---|
| conflict-handling recall (flag/resolve vs silently answer one side) | **0%** | **100%** (5/5) |
| false-positive rate on consistent questions | 0% | **0%** |

This is the end-to-end analogue of the component detection F1 (0.948): naive RAG
silently answers conflicting sources; ConflictRAG flags/resolves all of them, without
false-flagging consistent questions — and, on the real arxiv KB, general questions still
answer normally (no over-triggering). Precision comes from filtering citations/reference
lines (their publication years were causing spurious temporal conflicts).

## 6b. Conflict over-triggering fix (2026-08-31)

**Problem:** on a KB of *related* documents (e.g. many arxiv papers), whole-chunk NLI
flagged almost every question as "sources disagree" — ConflictRAG felt like a conflict
detector, not "normal RAG but better".

**Fix (`conflict.py`):** a conflict now requires ALL of —
1. **sentence-level** comparison: each source's claim sentence most relevant to the
   question (via local MiniLM, `app/embed.py`), not whole 800-char chunks;
2. a **junk filter** that drops titles, author lines, references, formula fragments
   (the biggest false-positive source);
3. **high contradiction** (>= `DETECT_THRESHOLD` 0.85), both NLI directions;
4. a **concrete structured cue about a SHARED subject** — different numbers/dates or a
   negation/antonym — matching the Factual/Temporal/Contradictory taxonomy.

**Two thresholds, on purpose:** `CONFLICT_THRESHOLD` (0.6) is NLI separability on the
short benchmark claim pairs (run_eval.py, F1 0.948); `DETECT_THRESHOLD` (0.85) is the
deployed pipeline's stricter bar on long real documents. Verified: general questions
answer normally (confident); the office-days / travel-allowance conflicts are still caught.

## 6a. Latest session changes (2026-08-29)

- **Relevance gate** (`pipeline.py`, `MIN_RELEVANCE = 0.35`): a query whose best chunk scores below the
  threshold returns `not_found` instead of forcing an answer/false conflict. Fixes "hi" -> fake conflict.
- **View files**: `GET /documents/view?name=` serves the PDF; the FE opens it in an in-app viewer modal.
- **Delete files/folders**: `DELETE /documents?name=` (Chroma + SQLite) and `DELETE /folders/{id}`; FE has
  hover trash buttons + a confirm modal.
- **Upload progress**: FE shows a per-file "Processing… reading, chunking & embedding" banner during ingest.
- **Chat history fix**: `/ask` now stores the full response JSON; `GET /conversations/{cid}` reopens a saved
  chat without re-running the pipeline (no more duplicate conversations).
- All verified live in the browser against the running backend.

## 7. What is LEFT to build (by area, priority order)

**Backend (Noor):**
- [ ] **RAGAS evaluation** (Phase 5): faithfulness / answer-relevance / context-precision-recall,
      baseline (mode="baseline") vs conflictrag, on the full answer pipeline. **THIS is the #1 remaining paper number.**
- [x] ~~Persistent storage / folders~~ — DONE. `db.py` (SQLite): folders, documents, conversations, messages;
      survives restarts; folder-explorer works. No seed data (starts empty, reflects only real user actions).
- [ ] **Agent-trace emission**: have the pipeline record each step (retrieve -> detect -> classify -> reconcile ->
      generate) and expose it in the `/ask` response so the frontend Trace UI can render it. (Not started.)
- [ ] (stretch, "full CARL" per proposal) multi-hop retrieval; ReAct tool verification (web/calc/python); token streaming.
- [ ] Docker packaging (Phase 6) for one-command self-hosting.
- Backlog quality items (see `BACKLOG.md`): citations = used-not-retrieved; drop low-relevance related_sources;
      sentence-level conflict detection; prune NLI pairs for speed; tune the relevance gate threshold (currently 0.35).

**Frontend (Chetan's contribution — Noor built a working version as a safety net):**
- [x] ~~Real React (Vite + TS) app~~ — DONE and wired to the live API through `src/api.ts`.
- [x] ~~Render all 4 response types + related_sources~~ — DONE.
- [x] ~~Functional upload~~ — DONE, with a live "Processing…" banner per file.
- [x] ~~Windows folder-explorer look~~ — DONE (this became the primary design).
- [x] ~~View / delete files + folders~~ — DONE (PDF preview modal; hover-to-delete with confirm).
- [ ] **Agent-Trace UI** (NEW — not in the mockups): collapsible panel showing the reasoning steps
      (blocked on the backend agent-trace emission above).
- [ ] Attach / paperclip flow that scopes a question to "this document + KB" (button exists; opens file picker; not yet scoped).
- [ ] Polish: Sort / View toolbar buttons are still decorative; a Trash view that actually restores/purges.

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

# frontend (Chetan's; runs on :5173, calls the backend on :8000)
cd conflictRAG/frontend
npm install
npm run dev                   # open http://localhost:5173
```

> **Windows/Vite gotcha:** if the app renders blank with a `ReferenceError` for a symbol that no longer
> exists in the source, Vite's file watcher missed a save and is serving a stale transform. Hard-refresh
> (Ctrl+Shift+R); if still broken, restart `npm run dev`. This is not a code bug.

## 10. Key facts to not get wrong

- ConflictRAG is candora's successor idea done properly. Candora was a finance-scoped hackathon prototype.
- CARL = Conflict-Aware Reasoning **Layer** (R = Reasoning). Reconciliation is a step *inside* the reasoning.
- The privacy claim REQUIRES the LLM to be local (Ollama), never a cloud API — this is core, not optional.
- Detection is excellent (96%); classification is the weak secondary metric (72%, documented). Don't over-claim.
