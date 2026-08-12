from app.retrieve import retrieve
from app.generate import generate_answer
from app.store import get_collection


def answer_question(question: str, mode: str = "conflictrag") -> dict:
    """Run the full pipeline and return a response shaped like docs/api-contract.md.

    Types: not_found | confident | conflict (conflict is added in Phase 2).
    """
    if get_collection().count() == 0:
        return {"type": "not_found",
                "message": "The knowledge base is empty. Add a source first."}

    hits = retrieve(question)

    # === Phase 2 (CARL) plugs in HERE ===
    # The sufficiency check + NLI conflict detection will decide between
    # confident / not_found / conflict. For now, any retrieval → 'confident'.

    answer = generate_answer(question, hits, mode=mode)
    citations = [{"doc": h["title"], "page": h["page"], "snippet": h["text"][:160]}
                 for h in hits]
    return {"type": "confident", "answer": answer, "citations": citations}