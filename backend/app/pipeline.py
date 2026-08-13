from app.config import settings
from app.retrieve import retrieve
from app.generate import generate_answer
from app.conflict import detect_conflicts, reconcile
from app.store import get_collection

RELATED_K = 8


def _related_sources(hits):
    seen = {}
    for h in hits:
        if h["source"] not in seen:
            seen[h["source"]] = {"doc": h["title"], "page": h["page"],
                                 "excerpt": h["text"][:160], "relevance": h["score"]}
    return list(seen.values())


def answer_question(question: str, mode: str = "conflictrag") -> dict:
    if get_collection().count() == 0:
        return {"type": "not_found",
                "message": "The knowledge base is empty. Add a source first."}

    hits_all = retrieve(question, top_k=RELATED_K)
    hits = hits_all[:settings.top_k]
    related = _related_sources(hits_all)

    if mode == "conflictrag":
        conflicts = detect_conflicts(hits_all)
        if conflicts:
            reconciled = reconcile(conflicts[0])

            if reconciled["resolvable"]:                       # revision -> answer + note
                gov, sup = reconciled["governing"], reconciled["superseded"]
                gov_hit = {"text": gov["excerpt"], "title": gov["doc"], "page": gov["page"]}
                answer = generate_answer(question, [gov_hit], mode=mode)
                return {
                    "type": "resolved",
                    "conflict_kind": reconciled["kind"],
                    "answer": answer,
                    "governing": gov,
                    "superseded": sup,
                    "note": f"This supersedes an earlier value from {sup['doc']}.",
                    "related_sources": related,
                }

            top = conflicts[0]                                 # genuine -> halt and ask
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