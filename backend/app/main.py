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
    attachment_id: str | None = None


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
    """Delete a document: its chunks from ChromaDB AND its metadata row."""
    get_collection().delete(where={"source": name})   # gone from the vector store
    db.delete_document(name)                           # gone from the file list
    return {"deleted": name}


@app.get("/conversations")
def get_conversations():
    return db.list_conversations()


@app.post("/ingest")
async def ingest(file: UploadFile = File(...), folder: str | None = Form(None)):
    dest = settings.upload_dir / file.filename
    dest.write_bytes(await file.read())
    ingest_pdf(dest)                                 # content + vectors -> ChromaDB
    size = f"{dest.stat().st_size / 1_000_000:.1f} MB"
    db.add_document(file.filename, folder, size)     # metadata -> SQLite
    return {"doc_id": file.filename, "name": file.filename, "status": "ready"}


@app.post("/ask")
def ask(req: AskRequest):
    res = answer_question(req.question)
    res.setdefault("related_sources", [])

    # "evidence" = the files behind the answer, so the middle pane can list them
    res["evidence"] = [{
        "id": rs["doc"],
        "name": rs["doc"] if str(rs["doc"]).endswith(".pdf") else f'{rs["doc"]}.pdf',
        "folder": db.folder_of(rs["doc"]),
        "date": "—", "type": "PDF Document", "size": "—", "status": "ready",
    } for rs in res["related_sources"]]

    # save the conversation (store the FULL response so the chat can be reopened
    # later WITHOUT re-running the pipeline)
    cid = db.create_conversation(req.question)
    res["conversation_id"] = cid
    db.add_message(cid, "user", req.question)
    db.add_message(cid, "assistant", json.dumps(res, ensure_ascii=False), res["type"])
    return res


@app.get("/conversations/{cid}")
def get_conversation(cid: str):
    return db.get_conversation(cid)
