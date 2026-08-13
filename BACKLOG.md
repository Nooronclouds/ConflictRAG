# ConflictRAG — Backlog (things deliberately deferred)

## Backend
- [ ] Citations: return only the sources the answer actually *used*, not all retrieved chunks.
- [ ] Ingestion: move from in-memory status to a DB-backed job store (survives restarts).
- [ ] Retrieval: filter out low-relevance chunks (e.g. acknowledgements pages) before generation.
- [ ] Folders: real folder structure for the knowledge base (currently flat).

## Product
- [ ] Attachment flow: "ask about this document + KB" (the paperclip path).
- [ ] "Conflicts" view: proactively list contradictions across the KB.

## Research
- [ ] Grow the conflict eval set beyond the starter (target 30–50+, add negatives).

## API contract
- [ ] Update docs/api-contract.md: conflict `sources` use `excerpt` (+ doc, page), matching pipeline output. Sync with Chetan.

## Research / CARL accuracy
- [ ] Taxonomy classifier: current type is a regex heuristic (checks "year" before "number"), so a value-change-with-dates is labeled `temporal`, not `factual`. Upgrade to a proper classifier.
- [ ] Sentence-level conflict detection: NLI currently compares whole ~800-char chunks; extract claims/sentences to reduce false positives on real documents.