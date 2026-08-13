import re
from itertools import combinations
from app.nli import check_pair

CONFLICT_THRESHOLD = 0.6   # min contradiction score to call it a conflict


def classify_conflict(a: str, b: str) -> str:
    """Guess the conflict type from the text (simple heuristic — v1)."""
    year = re.compile(r"\b(19|20)\d{2}\b")
    if year.search(a) and year.search(b):
        return "temporal"
    if re.search(r"\b\d+\b", a) and re.search(r"\b\d+\b", b):
        return "factual"
    return "contradictory"


def detect_conflicts(hits: list[dict]) -> list[dict]:
    """Compare retrieved chunks pairwise with NLI; return any contradicting pairs."""
    conflicts = []
    for h1, h2 in combinations(hits, 2):
        # Compare chunks from DIFFERENT documents only — a document 'contradicting
        # itself' is usually just chunk-boundary noise. Cross-doc is the real signal.
        if h1["source"] == h2["source"]:
            continue
        result = check_pair(h1["text"], h2["text"])
        score = result["scores"]["contradiction"]
        if result["label"] == "contradiction" and score >= CONFLICT_THRESHOLD:
            conflicts.append({
                "kind": classify_conflict(h1["text"], h2["text"]),
                "score": round(score, 3),
                "sources": [
                    {"doc": h1["title"], "page": h1["page"], "excerpt": h1["text"][:200]},
                    {"doc": h2["title"], "page": h2["page"], "excerpt": h2["text"][:200]},
                ],
            })
    conflicts.sort(key=lambda c: c["score"], reverse=True)   # strongest first
    return conflicts