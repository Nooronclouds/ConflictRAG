from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.store import get_collection
from app.ingest import ingest_pdf
from app.pipeline import answer_question

app = FastAPI(title="ConflictRAG API")

# Let the frontend (a different port in dev) call this API.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_methods=["*"], allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    attachment_id: str | None = None


@app.get("/documents")
def list_documents():
    """List the documents in the knowledge base (derived from stored chunks)."""
    data = get_collection().get(include=["metadatas"])
    seen = {}
    for meta in data["metadatas"]:
        src = meta.get("source")
        if src and src not in seen:
            seen[src] = {"id": src, "name": meta.get("title", src),
                         "folder": None, "status": "ready", "pages": None, "added": None}
    return {"folders": [], "files": list(seen.values())}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    """Upload a PDF and add it to the knowledge base."""
    dest = settings.upload_dir / file.filename
    dest.write_bytes(await file.read())
    chunks = ingest_pdf(dest)
    return {"doc_id": file.filename, "name": file.filename, "status": "ready", "chunks": chunks}


@app.post("/ask")
def ask(req: AskRequest):
    """Answer a question from the knowledge base."""
    return answer_question(req.question)