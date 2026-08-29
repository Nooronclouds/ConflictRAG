import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.ingest import ingest_pdf
from app.pipeline import answer_question
from app.store import get_collection
from app import db

app = FastAPI(title="ConflictRAG API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

db.init_db()   # create the tables on startup


class AskRequest(BaseModel):
    question: str
    attachment_id: str | None = None      # if set, scope retrieval to this one document
    conversation_id: str | None = None    # if set, append to an existing chat thread


class FolderRequest(BaseModel):
    name: str


@app.get("/folders")
def get_folders():
    return db.list_folders()


@app.post("/folders")
def make_folder(req: FolderRequest):
    fid = db.add_folder(req.name)
    return {"id": fid, "name": req.name}


@app.get("/documents")
def get_documents(folder: str | None = None):
    return db.list_documents(folder)


@app.get("/trash")
def get_trash():
    return db.list_trash()


@app.delete("/folders/{fid}")
def remove_folder(fid: str):
    db.delete_folder(fid)
    return {"deleted": fid}


@app.get("/documents/view")
def view_document(name: str):
    """Serve the raw PDF so the frontend can open/preview it."""
    path = settings.upload_dir / name
    if not path.exists():
        raise HTTPException(404, f"File not found: {name}")
    # inline (not attachment) so the browser RENDERS the PDF in the iframe
    # instead of triggering a download/save dialog
    return FileResponse(str(path), media_type="application/pdf", content_disposition_type="inline")


@app.delete("/documents")
def remove_document(name: str):
    """Soft delete → Trash. Remove its vectors so the Librarian stops using it,
    but keep the row and the PDF file so it can be restored."""
    get_collection().delete(where={"source": name})   # out of the knowledge base
    db.delete_document(name)                           # marked trashed (still restorable)
    return {"trashed": name}


@app.post("/documents/restore")
def restore_document(name: str):
    """Bring a document back from Trash: re-index its PDF and unmark it."""
    path = settings.upload_dir / name
    if path.exists():
        ingest_pdf(path)                               # back into the vector store
    db.restore_document(name)
    return {"restored": name}


@app.delete("/documents/purge")
def purge_document(name: str):
    """Permanently delete a trashed document: row + vectors + the PDF file."""
    get_collection().delete(where={"source": name})    # in case any vectors remain
    db.purge_document(name)
    path = settings.upload_dir / name
    if path.exists():
        path.unlink()
    return {"purged": name}


@app.get("/conversations")
def get_conversations():
    return db.list_conversations()


@app.post("/ingest")
async def ingest(file: UploadFile = File(...), folder: str | None = Form(None)):
    dest = settings.upload_dir / file.filename
    dest.write_bytes(await file.read())

    # Re-uploading the same filename REPLACES the old copy instead of duplicating it
    # (old bug: same file ingested N times -> N rows + N copies of every chunk).
    if db.document_exists(file.filename):
        get_collection().delete(where={"source": file.filename})
        db.purge_document(file.filename)

    ingest_pdf(dest)                                 # content + vectors -> ChromaDB
    size = f"{dest.stat().st_size / 1_000_000:.1f} MB"
    db.add_document(file.filename, folder, size)     # metadata -> SQLite
    return {"doc_id": file.filename, "name": file.filename, "status": "ready"}


@app.post("/ask")
def ask(req: AskRequest):
    res = answer_question(req.question, scope=req.attachment_id)
    res.setdefault("related_sources", [])

    # "evidence" = the files behind the answer, so the middle pane can list them
    res["evidence"] = [{
        "id": rs["doc"],
        "name": rs["doc"] if str(rs["doc"]).endswith(".pdf") else f'{rs["doc"]}.pdf',
        "folder": db.folder_of(rs["doc"]),
        "date": "—", "type": "PDF Document", "size": "—", "status": "ready",
    } for rs in res["related_sources"]]

    # Thread the chat: reuse the conversation if one was passed (a follow-up),
    # otherwise start a new one. Store the FULL response so it can be reopened later.
    cid = req.conversation_id or db.create_conversation(req.question)
    res["conversation_id"] = cid
    db.add_message(cid, "user", req.question)
    db.add_message(cid, "assistant", json.dumps(res, ensure_ascii=False), res["type"])
    return res


@app.get("/conversations/{cid}")
def get_conversation(cid: str):
    return db.get_conversation(cid)


@app.delete("/conversations/{cid}")
def remove_conversation(cid: str):
    db.delete_conversation(cid)
    return {"deleted": cid}
