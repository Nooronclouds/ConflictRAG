#Step 1 — connection helper
import sqlite3, uuid, datetime, json
from app.config import settings

DB_PATH = settings.data_dir / "conflictrag.db"   # the database is one file on disk


def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row   # makes rows behave like dicts: row["name"]
    return c
#Step 2 — the tables (the schema)
def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS folders(
            id TEXT PRIMARY KEY, name TEXT, parent TEXT);

        CREATE TABLE IF NOT EXISTS documents(
            id TEXT PRIMARY KEY, name TEXT, folder TEXT,
            date TEXT, type TEXT, size TEXT, status TEXT, trashed INTEGER DEFAULT 0);

        CREATE TABLE IF NOT EXISTS conversations(
            id TEXT PRIMARY KEY, title TEXT, created_at TEXT);

        CREATE TABLE IF NOT EXISTS messages(
            id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT,
            content TEXT, response_type TEXT, created_at TEXT);
        """)
        # migration for databases created before the `trashed` column existed
        cols = [r["name"] for r in c.execute("PRAGMA table_info(documents)")]
        if "trashed" not in cols:
            c.execute("ALTER TABLE documents ADD COLUMN trashed INTEGER DEFAULT 0")
#Step 3 — folder creation (since we're not seeding folders)
def add_folder(name, parent=None):
    fid = str(uuid.uuid4())
    with _conn() as c:
        c.execute("INSERT INTO folders(id,name,parent) VALUES(?,?,?)", (fid, name, parent))
    return fid

#Step 4 — reading data (what the frontend's file explorer needs)
def list_folders():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT id,name FROM folders ORDER BY name")]


def list_documents(folder=None):
    """Live documents only (not in Trash)."""
    with _conn() as c:
        base = "SELECT id,name,folder,date,type,size,status FROM documents WHERE trashed=0"
        rows = c.execute(base + " AND folder=? ORDER BY name", (folder,)) if folder \
            else c.execute(base + " ORDER BY name")
        return [dict(r) for r in rows]


def list_trash():
    """Documents that have been soft-deleted."""
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT id,name,folder,date,type,size,status FROM documents WHERE trashed=1 ORDER BY name")]


def folder_of(doc_name):
    with _conn() as c:
        r = c.execute("SELECT folder FROM documents WHERE name=? OR name LIKE ?",
                      (doc_name, str(doc_name) + "%")).fetchone()
        return r["folder"] if r else None

#Step 5 — writing data (uploads + chat history)
def add_document(name, folder=None, size="—"):
    with _conn() as c:
        c.execute("INSERT INTO documents(id,name,folder,date,type,size,status,trashed) VALUES(?,?,?,?,?,?,?,0)",
                  (str(uuid.uuid4()), name, folder,
                   datetime.datetime.now().strftime("%d-%m-%Y %H:%M"), "PDF Document", size, "ready"))


def document_exists(name):
    with _conn() as c:
        return c.execute("SELECT 1 FROM documents WHERE name=?", (name,)).fetchone() is not None


def delete_document(name):
    """Soft delete → move to Trash (keeps the row so it can be restored)."""
    with _conn() as c:
        c.execute("UPDATE documents SET trashed=1 WHERE name=?", (name,))


def restore_document(name):
    with _conn() as c:
        c.execute("UPDATE documents SET trashed=0 WHERE name=?", (name,))


def purge_document(name):
    """Permanent delete → remove the row entirely (caller also drops file + vectors)."""
    with _conn() as c:
        c.execute("DELETE FROM documents WHERE name=?", (name,))


def dedup_documents():
    """Collapse duplicate rows so each filename appears once (keeps the earliest,
    preferring one that sits in a folder). Returns how many rows were removed."""
    with _conn() as c:
        rows = c.execute("SELECT id, name, folder FROM documents ORDER BY name").fetchall()
        by_name = {}
        for r in rows:
            keep = by_name.get(r["name"])
            # prefer a copy that has a folder over one sitting at the root
            if keep is None or (keep["folder"] is None and r["folder"] is not None):
                by_name[r["name"]] = r
        keep_ids = {r["id"] for r in by_name.values()}
        removed = 0
        for r in rows:
            if r["id"] not in keep_ids:
                c.execute("DELETE FROM documents WHERE id=?", (r["id"],))
                removed += 1
    return removed


def delete_folder(fid):
    with _conn() as c:
        # move any documents inside back to the root, then drop the folder
        c.execute("UPDATE documents SET folder=NULL WHERE folder=?", (fid,))
        c.execute("DELETE FROM folders WHERE id=?", (fid,))


def create_conversation(question):
    cid = str(uuid.uuid4())
    with _conn() as c:
        c.execute("INSERT INTO conversations(id,title,created_at) VALUES(?,?,?)",
                  (cid, question[:60], datetime.datetime.now().isoformat()))
    return cid


def add_message(cid, role, content, rtype=None):
    with _conn() as c:
        c.execute("INSERT INTO messages(id,conversation_id,role,content,response_type,created_at) VALUES(?,?,?,?,?,?)",
                  (str(uuid.uuid4()), cid, role, content, rtype, datetime.datetime.now().isoformat()))


def delete_conversation(cid):
    with _conn() as c:
        c.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
        c.execute("DELETE FROM conversations WHERE id=?", (cid,))


def list_conversations():
    with _conn() as c:
        rows = c.execute("SELECT id,title,created_at FROM conversations ORDER BY created_at DESC LIMIT 30")
        out = []
        for r in rows:
            days = (datetime.datetime.now() - datetime.datetime.fromisoformat(r["created_at"])).days
            when = "Today" if days == 0 else "Yesterday" if days == 1 else f"{days} days ago"
            out.append({"id": r["id"], "title": r["title"], "question": r["title"], "when": when})
        return out


def get_conversation(cid):
    """Return the whole conversation as an ordered list of turns:
    {id, turns: [{question, response}, ...]}."""
    with _conn() as c:
        conv = c.execute("SELECT id, title FROM conversations WHERE id=?", (cid,)).fetchone()
        if not conv:
            return None
        msgs = c.execute(
            "SELECT role, content, response_type FROM messages WHERE conversation_id=? ORDER BY created_at",
            (cid,)).fetchall()

    turns, pending_q = [], None
    for m in msgs:
        if m["role"] == "user":
            pending_q = m["content"]
        elif m["role"] == "assistant":
            try:
                response = json.loads(m["content"])            # full saved answer
            except Exception:
                response = {"type": m["response_type"] or "not_found",
                            "message": m["content"], "related_sources": [], "evidence": []}
            turns.append({"question": pending_q, "response": response})
            pending_q = None
    return {"id": conv["id"], "turns": turns}
    