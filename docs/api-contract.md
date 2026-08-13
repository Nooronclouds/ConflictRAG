# ConflictRAG — Frontend API Contract (v1, frozen)

The frontend is built against these shapes. Field names are fixed — do not rename them,
so that swapping mock data for the real backend is a one-file change.

Base URL (local): `http://localhost:8000`

---

## 1. List the knowledge base
`GET /documents`

```json
{
  "folders": [
    { "id": "policies", "name": "Policies", "parent": null },
    { "id": "contracts", "name": "Contracts", "parent": null }
  ],
  "files": [
    { "id": "doc_01", "name": "Leave policy v1.pdf", "folder": "policies",
      "status": "ready", "pages": 12, "added": "2026-08-01" },
    { "id": "doc_02", "name": "Travel expenses.pdf", "folder": "policies",
      "status": "processing", "pages": null, "added": "2026-08-12" }
  ]
}
```
`status` = `"ready"` | `"processing"` | `"failed"` → drives the file-list badge color.

---
## 2. Ask a question — POST /ask  (updated: 4 types + related_sources)

Request: `{ "question": "...", "attachment_id": null }`

Every response has a `type` AND a `related_sources` array (the reading list).

### 2a. Confident
```json
{
  "type": "confident",
  "answer": "...",
  "citations": [ { "doc": "...", "page": 3, "snippet": "..." } ],
  "related_sources": [ { "doc": "...", "page": 1, "excerpt": "...", "relevance": 0.66 } ]
}
```

### 2b. Resolved  (NEW — a conflict that was a revision)
```json
{
  "type": "resolved",
  "conflict_kind": "temporal",
  "answer": "The current travel allowance is ₹250/day, per the 2025 addendum.",
  "governing":  { "doc": "Travel Addendum",  "page": 1, "excerpt": "...revised to ₹250...2025" },
  "superseded": { "doc": "Travel Policy v1", "page": 1, "excerpt": "...₹500...2021" },
  "note": "This supersedes an earlier value from Travel Policy v1.",
  "related_sources": [ ... ]
}
```

### 2c. Conflict  (genuine — halt and ask)
```json
{
  "type": "conflict",
  "conflict_kind": "factual",
  "question_summary": "...",
  "sources": [ { "doc": "...", "page": 4, "excerpt": "..." }, { "doc": "...", "page": 2, "excerpt": "..." } ],
  "suggestion": "These sources disagree — please review which one applies.",
  "related_sources": [ ... ]
}
```

### 2d. Not found
```json
{ "type": "not_found", "message": "..." }
```

## related_sources (shared component)
Each item: `{ "doc": "...", "page": 1, "excerpt": "...", "relevance": 0.66 }`.
Render as a "Related in your knowledge base" reading list under every answer, each row openable.
## 3. Upload a document
`POST /ingest` (multipart file upload)

```json
{ "doc_id": "doc_07", "name": "New contract.pdf", "status": "processing" }
```
The UI then polls `GET /documents` until that doc's `status` becomes `"ready"`.

---

## Rule for the frontend
All data flows through ONE module (`src/api.ts`). Today it returns the mock JSON above;
later it does real `fetch()` calls to these endpoints. Keep it in one file so the swap is trivial.