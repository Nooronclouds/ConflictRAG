from pathlib import Path
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.store import get_collection
from app.ingest import ingest_pdf
from app.pipeline import answer_question

app = FastAPI(title="ConflictRAG API")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_methods=["*"], allow_headers=["*"],
)

# In-memory registry of documents and their ingestion status.
# (Resets on restart — fine for now; we re-seed it from the store below.)
DOCUMENTS: dict[str, dict] = {}


def _seed_registry_from_store():
    """On startup, list already-ingested docs from Chroma as 'ready'."""
    data = get_collection().get(include=["metadatas"])
    for meta in data["metadatas"]:
        src = meta.get("source")
        if src and src not in DOCUMENTS:
            DOCUMENTS[src] = {"id": src, "name": meta.get("title", src),
                              "folder": None, "status": "ready", "pages": None, "added": None}


_seed_registry_from_store()


class AskRequest(BaseModel):
    question: str
    attachment_id: str | None = None


def _process_document(doc_id: str, path: Path):
    """Runs in the background: ingest the PDF, then flip status ready/failed."""
    try:
        ingest_pdf(path)
        DOCUMENTS[doc_id]["status"] = "ready"
    except Exception:
        DOCUMENTS[doc_id]["status"] = "failed"


@app.get("/documents")
def list_documents():
    """List documents and their live ingestion status."""
    return {"folders": [], "files": list(DOCUMENTS.values())}


@app.post("/ingest")
async def ingest(background: BackgroundTasks, file: UploadFile = File(...)):
    """Accept a PDF, return immediately as 'processing', ingest in the background."""
    dest = settings.upload_dir / file.filename
    dest.write_bytes(await file.read())

    doc_id = file.filename
    DOCUMENTS[doc_id] = {"id": doc_id, "name": file.filename, "folder": None,
                         "status": "processing", "pages": None, "added": None}
    background.add_task(_process_document, doc_id, dest)
    return {"doc_id": doc_id, "name": file.filename, "status": "processing"}


@app.post("/ask")
def ask(req: AskRequest):
    return answer_question(req.question)