import re
from itertools import combinations
from app.nli import check_pair
from app.embed import embed_texts   # shared local MiniLM encoder

# CONFLICT_THRESHOLD — NLI separability on the (short) benchmark claim pairs; used
# by run_eval.py. Kept at 0.6 where it gives the reported detection F1.
CONFLICT_THRESHOLD = 0.6

# DETECT_THRESHOLD — the DEPLOYED pipeline's bar on long, real documents. Higher,
# because whole-document NLI over a corpus of related papers fires constantly (two
# papers discussing a topic differently is NOT a user-facing conflict). Combined
# with the structural gates below, this keeps only genuine "same fact, different
# value" clashes.
DETECT_THRESHOLD = 0.85

REVISION_WORDS = ["revised", "amended", "amendment", "supersede", "superseded",
                  "effective", "updated", "addendum", "with effect from", "w.e.f"]

NEG = re.compile(r"\b(not|no|never|cannot|can't|without|isn't|aren't|don't)\b")
ANTONYMS = [("allowed", "prohibited"), ("allowed", "banned"), ("permitted", "prohibited"),
            ("permitted", "banned"), ("mandatory", "optional"), ("required", "optional"),
            ("eligible", "ineligible"), ("legal", "illegal"), ("valid", "invalid"),
            ("required", "not required")]

# Reference / citation markers — bibliography entries leak publication years that
# fire spurious "temporal" conflicts, so they must never be treated as claims.
_CITATION = re.compile(r"\b(et al|arxiv|preprint|proceedings|conference on|journal of|pp\.|vol\.|doi)\b", re.I)
_CITE_YEAR_END = re.compile(r",\s*(?:19|20)\d{2}[a-z]?\.?\s*$")   # "..., 2024."
_ARXIV_ID = re.compile(r"\b\d{4}\.\d{4,5}\b")                      # "2506.05154"

_STOP = {"the", "and", "that", "this", "with", "from", "have", "which", "their", "there",
         "these", "those", "about", "large", "language", "models", "model", "using", "based",
         "such", "when", "what", "into", "than", "them", "they", "were", "will", "would",
         "shahul", "james", "espinosa", "retrieval", "generation", "paper", "proposed",
         "framework", "approach", "method", "results", "section", "figure", "table"}


def _latest_year(text: str):
    years = [int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", text)]
    return max(years) if years else None


def _keywords(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{5,}", text.lower()) if w not in _STOP}


def _is_prose(sentence: str) -> bool:
    """Reject titles, author lines, reference entries, formula/symbol fragments —
    they aren't factual claims and are the main source of false conflicts."""
    s = sentence.strip()
    words = s.split()
    if len(words) < 6:
        return False
    if _CITATION.search(s) or _CITE_YEAR_END.search(s) or _ARXIV_ID.search(s):
        return False                      # bibliography / citation, not a claim
    letters = [c for c in s if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.4:
        return False                      # mostly-capitalised → an ALL-CAPS heading
    if sum(not c.isalnum() and not c.isspace() for c in s) > len(s) * 0.25:
        return False                      # symbol-heavy → math / citations
    # Title / author lines have most words Capitalised; real prose does not.
    capitalised = sum(1 for w in words if w[:1].isupper())
    if capitalised / len(words) > 0.5:
        return False
    return True


def _numbers(text: str) -> list:
    # ignore 4-digit years here; those are handled as Temporal
    return [n for n in re.findall(r"\b\d+(?:\.\d+)?\b", text) if not re.fullmatch(r"(?:19|20)\d{2}", n)]


def classify_conflict(a: str, b: str) -> str:
    la, lb = a.lower(), b.lower()
    if bool(NEG.search(la)) != bool(NEG.search(lb)):
        return "contradictory"
    for x, y in ANTONYMS:
        if (x in la and y in lb) or (y in la and x in lb):
            return "contradictory"
    ya, yb = _latest_year(la), _latest_year(lb)
    if (ya or yb) and ya != yb:
        return "temporal"
    if _numbers(la) != _numbers(lb):
        return "factual"
    return "contradictory"


def _concrete_cue(a: str, b: str) -> bool:
    """True only when the two claims carry a STRUCTURED disagreement about a
    shared subject — not just NLI 'vibes'."""
    la, lb = a.lower(), b.lower()
    shared = _keywords(la) & _keywords(lb)          # same subject matter?
    if not shared:
        return False

    # negation asymmetry on a shared subject
    if bool(NEG.search(la)) != bool(NEG.search(lb)):
        return True
    # antonym split
    for x, y in ANTONYMS:
        if (x in la and y in lb) or (y in la and x in lb):
            return True
    # different year (revision / timeline)
    ya, yb = _latest_year(la), _latest_year(lb)
    if (ya or yb) and ya != yb:
        return True
    # different numeric value about the same subject
    na, nb = _numbers(la), _numbers(lb)
    if na and nb and na != nb:
        return True
    return False


def _claim(chunk: str, question: str | None) -> str:
    """The one prose sentence of a chunk most relevant to the question."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", chunk) if _is_prose(s)]
    if not sents:
        return ""
    if not question:
        return sents[0]
    qv = embed_texts([question])[0]
    svs = embed_texts(sents)
    best = max(range(len(sents)), key=lambda i: float((qv * svs[i]).sum()))
    return sents[best]


def detect_conflicts(hits: list[dict], question: str | None = None) -> list[dict]:
    conflicts = []
    for h1, h2 in combinations(hits, 2):
        if h1["source"] == h2["source"]:
            continue
        c1, c2 = _claim(h1["text"], question), _claim(h2["text"], question)
        if not c1 or not c2:
            continue
        score = max(check_pair(c1, c2)["scores"]["contradiction"],
                    check_pair(c2, c1)["scores"]["contradiction"])
        if score < DETECT_THRESHOLD:
            continue
        if not _concrete_cue(c1, c2):          # no structured signal → not a real conflict
            continue
        conflicts.append({
            "kind": classify_conflict(c1, c2),
            "score": round(score, 3),
            "sources": [
                {"doc": h1["title"], "page": h1["page"], "excerpt": c1[:200]},
                {"doc": h2["title"], "page": h2["page"], "excerpt": c2[:200]},
            ],
        })
    conflicts.sort(key=lambda c: c["score"], reverse=True)
    return conflicts


def reconcile(conflict: dict) -> dict:
    a, b = conflict["sources"][0], conflict["sources"][1]
    ta, tb = a["excerpt"].lower(), b["excerpt"].lower()
    ya, yb = _latest_year(ta), _latest_year(tb)

    governing = superseded = None
    if ya and yb and ya != yb:
        governing, superseded = (a, b) if ya > yb else (b, a)
    else:
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
