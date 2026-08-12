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