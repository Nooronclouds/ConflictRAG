from app.retrieve import retrieve
from app.generate import generate_answer
from app.conflict import detect_conflicts
from app.store import get_collection


def answer_question(question: str, mode: str = "conflictrag") -> dict:
    """Run the pipeline. Returns not_found | conflict | confident (see api-contract.md)."""
    if get_collection().count() == 0:
        return {"type": "not_found",
                "message": "The knowledge base is empty. Add a source first."}

    hits = retrieve(question)

    # === CARL === only runs in conflictrag mode; baseline skips it entirely.
    if mode == "conflictrag":
        conflicts = detect_conflicts(hits)
        if conflicts:
            top = conflicts[0]
            return {
                "type": "conflict",
                "conflict_kind": top["kind"],
                "question_summary": question,
                "sources": [{"doc": s["doc"], "page": s["page"], "excerpt": s["excerpt"]}
                            for s in top["sources"]],
                "suggestion": "These sources disagree — please review which one applies.",
            }

    # No conflict (or baseline mode): answer normally.
    answer = generate_answer(question, hits, mode=mode)
    citations = [{"doc": h["title"], "page": h["page"], "snippet": h["text"][:160]}
                 for h in hits]
    return {"type": "confident", "answer": answer, "citations": citations}