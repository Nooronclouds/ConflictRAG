from app.config import settings
from app.retrieve import retrieve
from app.generate import generate_answer
from app.conflict import detect_conflicts
from app.store import get_collection

RELATED_K = 8   # how many chunks to scan for the "related sources" reading list


def _related_sources(hits: list[dict]) -> list[dict]:
    """Collapse retrieved chunks into a per-document reading list (best chunk per doc)."""
    seen = {}
    for h in hits:
        if h["source"] not in seen:          # keep the highest-ranked chunk per document
            seen[h["source"]] = {"doc": h["title"], "page": h["page"],
                                 "excerpt": h["text"][:160], "relevance": h["score"]}
    return list(seen.values())


def answer_question(question: str, mode: str = "conflictrag") -> dict:
    if get_collection().count() == 0:
        return {"type": "not_found",
                "message": "The knowledge base is empty. Add a source first."}

    hits_all = retrieve(question, top_k=RELATED_K)   # broad set, retrieved once
    hits = hits_all[:settings.top_k]                 # top few to actually answer from
    related = _related_sources(hits_all)             # the "further reading" list

    if mode == "conflictrag":
        conflicts = detect_conflicts(hits_all)       # scan the broader set for conflicts
        if conflicts:
            top = conflicts[0]
            return {
                "type": "conflict",
                "conflict_kind": top["kind"],
                "question_summary": question,
                "sources": [{"doc": s["doc"], "page": s["page"], "excerpt": s["excerpt"]}
                            for s in top["sources"]],
                "suggestion": "These sources disagree — please review which one applies.",
                "related_sources": related,
            }

    answer = generate_answer(question, hits, mode=mode)
    citations = [{"doc": h["title"], "page": h["page"], "snippet": h["text"][:160]}
                 for h in hits]
    return {"type": "confident", "answer": answer,
            "citations": citations, "related_sources": related}