import time
from itertools import combinations
from app.config import settings
from app.retrieve import retrieve
from app.generate import generate_answer
from app.conflict import detect_conflicts, reconcile
from app.store import get_collection

RELATED_K = 8
MIN_RELEVANCE = 0.35   # below this, the query doesn't really match the KB → not_found


def _related_sources(hits):
    seen = {}
    for h in hits:
        if h["source"] not in seen:
            seen[h["source"]] = {"doc": h["title"], "page": h["page"],
                                 "excerpt": h["text"][:160], "relevance": h["score"]}
    return list(seen.values())


def answer_question(question: str, mode: str = "conflictrag") -> dict:
    trace = []
    
    if get_collection().count() == 0:
        return {"type": "not_found",
                "message": "The knowledge base is empty. Add a source first.",
                "trace": trace}

    t0 = time.perf_counter()
    hits_all = retrieve(question, top_k=RELATED_K)
    ret_dur = int((time.perf_counter() - t0) * 1000)
    
    trace.append({
        "step": "retrieve",
        "label": f"Retrieved {len(hits_all)} chunks from knowledge base",
        "duration_ms": ret_dur,
        "result": "success",
        "details": {"query": question, "top_k": RELATED_K, "hits_count": len(hits_all), "best_score": hits_all[0]["score"] if hits_all else None}
    })

    # Relevance gate: a greeting like "hi" still returns the nearest chunks, but
    # they score low. If even the best hit is weak, the question isn't about the
    # KB — don't force an answer (or a false conflict).
    if not hits_all or hits_all[0]["score"] < MIN_RELEVANCE:
        return {"type": "not_found",
                "message": "I couldn't find anything about that in your knowledge base.",
                "trace": trace}

    # Keep only chunks that actually match the question. Retrieval always returns
    # top_k, so weak/irrelevant chunks come back too — running conflict detection
    # over those invents false conflicts between unrelated documents. Everything
    # downstream (detect, related list, generation) uses this filtered set.
    relevant = [h for h in hits_all if h["score"] >= MIN_RELEVANCE]
    hits = relevant[:settings.top_k]
    related = _related_sources(relevant)

    trace.append({
        "step": "filter",
        "label": f"Kept {len(relevant)} of {len(hits_all)} chunks above relevance {MIN_RELEVANCE}",
        "duration_ms": 0,
        "result": "success",
        "details": {"min_relevance": MIN_RELEVANCE, "kept": len(relevant), "dropped": len(hits_all) - len(relevant)}
    })

    if mode == "conflictrag":
        t0 = time.perf_counter()
        conflicts = detect_conflicts(relevant)
        det_dur = int((time.perf_counter() - t0) * 1000)

        pairs_count = sum(1 for a, b in combinations(relevant, 2) if a["source"] != b["source"])
        trace.append({
            "step": "detect",
            "label": f"Detected {len(conflicts)} conflicts",
            "duration_ms": det_dur,
            "result": "success",
            "details": {"pairs_checked": pairs_count, "conflicts_found": len(conflicts), "top_score": conflicts[0]["score"] if conflicts else None}
        })
        
        if conflicts:
            trace.append({
                "step": "classify",
                "label": "Classified conflict",
                "duration_ms": 0,
                "result": "success",
                "details": {"kind": conflicts[0]["kind"]}
            })
            
            t0 = time.perf_counter()
            reconciled = reconcile(conflicts[0])
            rec_dur = int((time.perf_counter() - t0) * 1000)
            
            trace.append({
                "step": "reconcile",
                "label": "Reconciled conflict",
                "duration_ms": rec_dur,
                "result": "success",
                "details": {
                    "resolvable": reconciled["resolvable"],
                    "governing": reconciled.get("governing", {}).get("doc") if reconciled["resolvable"] else None
                }
            })

            if reconciled["resolvable"]:                       # revision -> answer + note
                gov, sup = reconciled["governing"], reconciled["superseded"]
                gov_hit = {"text": gov["excerpt"], "title": gov["doc"], "page": gov["page"]}
                
                t0 = time.perf_counter()
                answer = generate_answer(question, [gov_hit], mode=mode)
                gen_dur = int((time.perf_counter() - t0) * 1000)
                
                trace.append({
                    "step": "generate",
                    "label": "Generated answer",
                    "duration_ms": gen_dur,
                    "result": "success",
                    "details": {"model": settings.ollama_model, "mode": mode}
                })
                
                return {
                    "type": "resolved",
                    "conflict_kind": reconciled["kind"],
                    "answer": answer,
                    "governing": gov,
                    "superseded": sup,
                    "note": f"This supersedes an earlier value from {sup['doc']}.",
                    "related_sources": related,
                    "trace": trace,
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
                "trace": trace,
            }

    t0 = time.perf_counter()
    answer = generate_answer(question, hits, mode=mode)
    gen_dur = int((time.perf_counter() - t0) * 1000)
    
    trace.append({
        "step": "generate",
        "label": "Generated answer",
        "duration_ms": gen_dur,
        "result": "success",
        "details": {"model": settings.ollama_model, "mode": mode}
    })
    
    citations = [{"doc": h["title"], "page": h["page"], "snippet": h["text"][:160]}
                 for h in hits]
    return {"type": "confident", "answer": answer,
            "citations": citations, "related_sources": related, "trace": trace}
