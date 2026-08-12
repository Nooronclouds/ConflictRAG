import uuid
from pathlib import Path
from pypdf import PdfReader
from app.config import settings
from app.store import get_collection


def extract_text(pdf_path: Path) -> list[tuple[int, str]]:
    """Return [(page_number, page_text), ...] for a PDF, skipping empty pages."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i, text))
    return pages


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Slice a long string into overlapping windows of `size` characters."""
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap   # step forward, but keep `overlap` chars shared
    return chunks


def ingest_pdf(pdf_path: Path, doc_title: str | None = None) -> int:
    """Read a PDF, split it, embed and store the chunks. Returns how many chunks."""
    collection = get_collection()
    title = doc_title or pdf_path.stem

    ids, documents, metadatas = [], [], []
    for page_num, page_text in extract_text(pdf_path):
        for chunk in chunk_text(page_text, settings.chunk_size, settings.chunk_overlap):
            ids.append(str(uuid.uuid4()))          # a unique id per chunk
            documents.append(chunk)                # the text itself
            metadatas.append({                     # info we keep for citations
                "title": title,
                "page": page_num,
                "source": pdf_path.name,
            })

    if documents:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(documents)