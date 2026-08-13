import re
from itertools import combinations
from app.nli import check_pair

CONFLICT_THRESHOLD = 0.6

# Words that signal one document is revising/superseding another.
REVISION_WORDS = ["revised", "amended", "amendment", "supersede", "superseded",
                  "effective", "updated", "addendum", "with effect from", "w.e.f"]


def classify_conflict(a: str, b: str) -> str:
    if re.search(r"\b(19|20)\d{2}\b", a) and re.search(r"\b(19|20)\d{2}\b", b):
        return "temporal"
    if re.search(r"\b\d+\b", a) and re.search(r"\b\d+\b", b):
        return "factual"
    return "contradictory"


def detect_conflicts(hits: list[dict]) -> list[dict]:
    conflicts = []
    for h1, h2 in combinations(hits, 2):
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
    conflicts.sort(key=lambda c: c["score"], reverse=True)
    return conflicts


def _latest_year(text: str):
    years = [int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", text)]
    return max(years) if years else None


def reconcile(conflict: dict) -> dict:
    """Decide if a conflict is RESOLVABLE (a newer/revising source supersedes the other)
    or GENUINE (no resolution signal -> should halt and ask the user)."""
    a, b = conflict["sources"][0], conflict["sources"][1]
    ta, tb = a["excerpt"].lower(), b["excerpt"].lower()
    ya, yb = _latest_year(ta), _latest_year(tb)

    governing = superseded = None
    if ya and yb and ya != yb:                       # different dates -> newer governs
        governing, superseded = (a, b) if ya > yb else (b, a)
    else:                                            # else: which one uses revision language?
        a_rev = any(w in ta for w in REVISION_WORDS)
        b_rev = any(w in tb for w in REVISION_WORDS)
        if a_rev and not b_rev:
            governing, superseded = a, b
        elif b_rev and not a_rev:
            governing, superseded = b, a

    if governing:
        return {"resolvable": True, "kind": conflict["kind"],
                "governing": governing, "superseded": superseded}
    return {"resolvable": False, "kind": conflict["kind"], "sources": conflict["sources"]}