# ConflictRAG

**A conflict-aware, fully-private RAG system for document question-answering.**

Normal Retrieval-Augmented Generation (RAG) grounds answers in your documents — but
when two sources **disagree**, it silently picks one and answers with false
confidence. That is dangerous in legal, healthcare, and finance settings.

ConflictRAG adds a **Conflict-Aware Reasoning Layer (CARL)** that runs *before*
generation: it **detects** contradictions between sources, **classifies** them
(factual / temporal / contradictory), and either **resolves** them transparently
(when one source is a dated revision of another) or **halts and asks** the user.
It also refuses to answer when the knowledge base has no relevant source.

Everything runs **locally** — local LLM (Ollama), local embeddings, local vector DB —
so no document ever leaves the machine.

---

## Key results

| Evaluation | Result |
|---|---|
| Conflict **detection** (NLI, 795 benchmark pairs) | **F1 0.948** (precision 0.959, recall 0.937) |
| Conflict-type **classification** | **74.7%** (temporal & contradictory 100%, factual 34.2%) |
| **End-to-end** conflict handling (controlled, vs naive RAG) | **100% recall, 0% false-positive** (naive RAG: 0% recall) |

Reproduce with `python run_eval.py` and `python run_conflict_eval.py` (see below).

## How it works

```
Question
  → Retrieve            sentence-transformers MiniLM  +  ChromaDB
  → CARL
       detect           DeBERTa-v3 NLI (entailment / contradiction)
       classify         rule-based → factual | temporal | contradictory
       reconcile        recency / revision → governing vs superseded
  → Decide one of 4 response types (+ a related-sources reading list)
  → Generate            local LLM via Ollama (only for confident / resolved)
```

**Four response types:** `confident` (grounded answer + citations) · `resolved`
(revision — current value + a struck-through superseded note) · `conflict` (genuine
clash — halts, shows both sides) · `not_found` (honest refusal).

To avoid false alarms on large corpora of *related* documents, conflict detection
works at the **claim-sentence** level and only fires on a high-confidence
contradiction backed by a **concrete, structured cue about a shared subject**
(different numbers/dates, or a negation/antonym) — not on raw NLI noise.

## Quick start

### Option A — Docker (recommended)

Prerequisites: Docker + [Ollama](https://ollama.com) on the host.
```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
docker compose up --build          # then open http://localhost:5173
```
The knowledge base starts **empty**; upload PDFs from the UI. Full guide: [DOCKER.md](DOCKER.md).

### Option B — Local dev

```bash
# backend
cd backend
py -3.11 -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
ollama pull llama3.2:3b
uvicorn app.main:app --port 8000        # API + Swagger at :8000/docs

# frontend (separate terminal)
cd frontend
npm install
npm run dev                              # http://localhost:5173
```

## Evaluation

```bash
cd backend
python run_eval.py            # detection F1 + classification (795-pair benchmark)
python run_conflict_eval.py   # controlled end-to-end: baseline RAG vs ConflictRAG
```
`run_conflict_eval.py` ingests its **own** planted-conflict corpus into a separate
collection, so it needs no pre-existing KB and is fully reproducible.

## Repository layout

```
backend/
  app/            config, store (Chroma), ingest, retrieve, generate (Ollama),
                  nli (DeBERTa), conflict (CARL), pipeline, db (SQLite), main (API)
  run_eval.py, run_conflict_eval.py    evaluation scripts
frontend/         React 18 + Vite + TypeScript (file-explorer UI, Agent Trace panel)
docs/             PROJECT_STATUS.md (full hand-off), api-contract.md, wireframes/
```

## Stack

Python 3.11 · FastAPI · ChromaDB · sentence-transformers (MiniLM) ·
transformers (DeBERTa-v3-base NLI) · Ollama (llama3.2:3b) · React + Vite + TypeScript.

## Scope & limitations (honest)

- **Built:** conflict detection, taxonomy, reconciliation, 4 response types, private/local
  operation, React UI with Agent-Trace, SQLite persistence, Docker packaging.
- **Not built (future work):** multi-hop agentic (ReAct) retrieval, external tool
  verification (web/Python/calculator), token streaming, a trained conflict-type
  classifier, DeBERTa-v3-large. Cross-document NLI can over-fire on very large related
  corpora — mitigated by claim-level detection; a learned detector is future work.

## Team

B.E. (AI & ML) major project, Navkis College of Engineering / VTU, 2025–2026 —
Chethan Gowda E R, Khadeejathul Arfa, Meiraj Fathima, Noor Laiba Maheen.
Guide: Dr. Vinaykumar V N.
