import time
from itertools import combinations
from app.config import settings
from app.retrieve import retrieve
from app.generate import generate_answer
from app.conflict import detect_conflicts, reconcile
from app.store import get_collection

RELATED_K = 8
MIN_RELEVANCE = 0.35   # below this, the query doesn't really match the KB → not_found
REFUSAL_CEILING = 0.6  # trust an LLM refusal only when the match is this weak or weaker;
                       # above it the content is clearly present, so keep the answer

# The LLM is told to say it has "no source" when the context can't answer. Similarity
# alone can't tell a real question (0.48) from junk (0.47), so we also trust that refusal.
_REFUSAL_CUES = (
    "don't have a source", "do not have a source", "no source for",
    "cannot answer", "can't answer", "not have enough information",
    "does not contain", "doesn't contain",
    "no information about", "don't have any information", "do not have any information",
    "don't have information", "no relevant information",
)


def _is_sentinel_refusal(answer: str) -> bool:
    """The prompt asks the model to reply exactly NO_SOURCE when it has nothing."""
    return answer.strip().upper().replace(".", "").startswith("NO_SOURCE")


def _has_refusal_cue(answer: str) -> bool:
    a = answer.lower()
    return any(cue in a for cue in _REFUSAL_CUES)


def _is_weak_refusal(answer: str) -> bool:
    """Fallback for when the model ignores the sentinel: a SHORT reply that is
    basically a refusal (not a real answer that merely hedges)."""
    return len(answer.strip()) < 140 and _has_refusal_cue(answer)


def _related_sources(hits):
    seen = {}
    for h in hits:
        if h["source"] not in seen:
            seen[h["source"]] = {"doc": h["title"], "page": h["page"],
                                 "excerpt": h["text"][:160], "relevance": h["score"]}
    return list(seen.values())


def answer_question(question: str, mode: str = "conflictrag", scope: str | None = None) -> dict:
    trace = []

    if get_collection().count() == 0:
        return {"type": "not_found",
                "message": "The knowledge base is empty. Add a source first.",
                "trace": trace}

    t0 = time.perf_counter()
    hits_all = retrieve(question, top_k=RELATED_K, source=scope)
    ret_dur = int((time.perf_counter() - t0) * 1000)

    scope_label = f" (scoped to {scope})" if scope else ""
    trace.append({
        "step": "retrieve",
        "label": f"Retrieved {len(hits_all)} chunks from knowledge base{scope_label}",
        "duration_ms": ret_dur,
        "result": "success",
        "details": {"query": question, "top_k": RELATED_K, "scope": scope, "hits_count": len(hits_all), "best_score": hits_all[0]["score"] if hits_all else None}
    })

    # Relevance gate — ONLY for whole-KB questions. A greeting like "hi" returns
    # the nearest chunks but they score low, so we reject it. BUT when the user has
    # explicitly scoped to one document, we trust that choice: summary-style
    # questions ("what is this about?") don't match any single chunk and would be
    # wrongly rejected. If the doc truly can't answer, the LLM refusal catches it.
    if not hits_all:
        return {"type": "not_found",
                "message": "I couldn't find anything about that in your knowledge base.",
                "trace": trace}
    if not scope and hits_all[0]["score"] < MIN_RELEVANCE:
        return {"type": "not_found",
                "message": "I couldn't find anything about that in your knowledge base.",
                "trace": trace}

    # Keep only chunks that actually match the question. Retrieval always returns
    # top_k, so weak/irrelevant chunks come back too — running conflict detection
    # over those invents false conflicts between unrelated documents. Everything
    # downstream (detect, related list, generation) uses this filtered set.
    # When scoped to one doc, keep all its chunks (the user chose it); otherwise
    # drop weak/irrelevant chunks so conflict detection isn't fooled by noise.
    relevant = hits_all if scope else [h for h in hits_all if h["score"] >= MIN_RELEVANCE]
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
    
    # Decide if the model actually answered. A clean NO_SOURCE sentinel is always a
    # refusal. Otherwise, on a marginal match, a short refusal-shaped reply also
    # counts (junk that slipped past the similarity bar). A real answer that merely
    # hedges is kept.
    best = hits_all[0]["score"] if hits_all else 0.0
    if _is_sentinel_refusal(answer):
        refused = True
    elif scope:
        # scoped: the user chose this doc, so keep real (possibly long) summaries;
        # only a short refusal-shaped reply counts
        refused = _is_weak_refusal(answer)
    else:
        # whole-KB, marginal match: any refusal-shaped hedge means it isn't really here
        refused = best < REFUSAL_CEILING and _has_refusal_cue(answer)
    if refused:
        trace.append({
            "step": "generate",
            "label": "Model found no supporting source → not in KB",
            "duration_ms": gen_dur,
            "result": "no_answer",
            "details": {"model": settings.ollama_model, "mode": mode, "refused": True}
        })
        msg = (f"I couldn't find anything about that in \"{scope}\"." if scope
               else "I couldn't find anything about that in your knowledge base.")
        return {"type": "not_found", "message": msg, "related_sources": [], "trace": trace}

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
