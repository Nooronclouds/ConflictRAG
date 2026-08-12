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

## 2. Ask a question
`POST /ask`

Request:
```json
{ "question": "How many leave days do part-time staff get?", "attachment_id": null }
```
`attachment_id` is `null` for a normal knowledge-base question; it holds an uploaded
document's id for the "ask about this document + KB" flow.

The response ALWAYS has a `type` field — one of three shapes:

### 2a. Confident
```json
{
  "type": "confident",
  "answer": "Part-time staff receive 12 days of annual leave, prorated by hours.",
  "citations": [
    { "doc": "Leave policy v1", "page": 3, "snippet": "Part-time employees accrue 12 days…" }
  ]
}
```

### 2b. Conflict
```json
{
  "type": "conflict",
  "conflict_kind": "factual",
  "question_summary": "Daily travel allowance",
  "sources": [
    { "value": "₹500 / day", "doc": "Travel policy v1", "date": "2021", "page": 4 },
    { "value": "₹250 / day", "doc": "Expense addendum", "date": "2025", "page": 2 }
  ],
  "suggestion": "The 2025 addendum is newer — likely governing."
}
```
`conflict_kind` = `"factual"` | `"temporal"` | `"contradictory"`.

### 2c. Not found
```json
{
  "type": "not_found",
  "message": "None of the documents cover this. Add a source and I'll answer from it."
}
```

---

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