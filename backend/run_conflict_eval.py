"""
Controlled end-to-end conflict-handling evaluation (baseline RAG vs ConflictRAG).

This is the eval that matches the project's actual thesis. It does NOT use your
real KB — it ingests its OWN small corpus with PLANTED conflicts into a separate
ChromaDB collection ("conflictrag_eval"), so an empty user KB is fine and the run
is fully reproducible.

It measures two things the paper claims:
  1. Conflict-handling recall  — of the planted conflicts, how many does each mode
     FLAG (conflict) or RESOLVE, instead of silently answering with one side?
  2. False-positive rate       — on consistent (non-conflict) questions, how often
     does each mode WRONGLY cry "conflict"?

Run:
    cd conflictRAG/backend
    .venv\\Scripts\\activate
    python run_conflict_eval.py
"""
import warnings
warnings.filterwarnings("ignore")

# Isolate to a throwaway collection BEFORE anything touches the vector store.
from app.config import settings
settings.collection_name = "conflictrag_eval"

from app.store import get_collection
from app.ingest import ingest_text
from app.pipeline import answer_question

# --- Planted corpus: each conflict is a PAIR of docs that clash on one fact ------
# (title, text). Sources must be distinct so cross-source detection can fire.
CONFLICT_DOCS = [
    ("travel_policy_2021", "The annual travel allowance for employees is 500 dollars per year."),
    ("travel_policy_2025", "The annual travel allowance for employees has been revised to 250 dollars per year, effective 2025."),
    ("hall_spec_a",        "The main conference hall has a seating capacity of 200 people."),
    ("hall_spec_b",        "The main conference hall has a seating capacity of 350 people."),
    ("retention_old",      "The data retention policy requires records to be kept for 5 years, effective 2019."),
    ("retention_new",      "The data retention policy requires records to be kept for 7 years, effective 2023."),
    ("remote_hr",          "Remote work is mandatory for all engineering staff."),
    ("remote_ops",         "Remote work is optional for all engineering staff."),
    ("access_rule_a",      "Contractors are permitted to access the internal database."),
    ("access_rule_b",      "Contractors are prohibited from accessing the internal database."),
]

# Consistent corpus: single or agreeing sources — must NOT be flagged as conflicts.
CONSISTENT_DOCS = [
    ("company_founding",   "The company was founded in Bangalore in 2015."),
    ("support_hours",      "The support team operates from 9 AM to 6 PM on weekdays."),
    ("premium_plan",       "The premium subscription includes unlimited cloud storage and priority support."),
    ("holiday_notice_a",   "The office is closed on all national holidays."),
    ("holiday_notice_b",   "On national holidays, the office remains closed to all staff."),
    ("wifi_policy",        "Guest WiFi access is available in the reception area only."),
]

CONFLICT_Q = [
    "What is the annual travel allowance for employees?",
    "What is the seating capacity of the main conference hall?",
    "How many years must records be retained?",
    "Is remote work mandatory for engineering staff?",
    "Are contractors allowed to access the internal database?",
]

CONSISTENT_Q = [
    "Where was the company founded?",
    "What are the support team's working hours?",
    "What does the premium subscription include?",
    "Is the office open on national holidays?",
    "Where is guest WiFi available?",
]


def setup_corpus():
    col = get_collection()
    existing = col.get()
    if existing["ids"]:
        col.delete(ids=existing["ids"])          # fresh run
    for title, text in CONFLICT_DOCS + CONSISTENT_DOCS:
        ingest_text(text, title=title, source=title)
    print(f"Ingested {len(CONFLICT_DOCS) + len(CONSISTENT_DOCS)} docs into "
          f"'{settings.collection_name}' ({col.count()} chunks)\n")


def flagged(res: dict) -> bool:
    """The mode treated the query as a conflict (halted or transparently resolved)."""
    return res.get("type") in ("conflict", "resolved")


def run_set(questions, expect_conflict: bool):
    rows = []
    for q in questions:
        b = answer_question(q, mode="baseline")
        c = answer_question(q, mode="conflictrag")
        rows.append((q, b["type"], c["type"], flagged(b), flagged(c)))
        mark = "conflict" if expect_conflict else "consistent"
        print(f"  [{mark}] baseline={b['type']:10} conflictrag={c['type']:10} | {q}")
    return rows


def main():
    setup_corpus()

    print("=== PLANTED CONFLICTS (want ConflictRAG to flag/resolve) ===")
    conf = run_set(CONFLICT_Q, expect_conflict=True)
    print("\n=== CONSISTENT QUESTIONS (want NEITHER to flag) ===")
    cons = run_set(CONSISTENT_Q, expect_conflict=False)

    nc = len(conf); ns = len(cons)
    b_recall = sum(1 for r in conf if r[3]) / nc
    c_recall = sum(1 for r in conf if r[4]) / nc
    b_fpr = sum(1 for r in cons if r[3]) / ns
    c_fpr = sum(1 for r in cons if r[4]) / ns

    print("\n" + "=" * 60)
    print(f"{'metric':<34}{'baseline':>12}{'conflictrag':>14}"[:60])
    print("-" * 60)
    print(f"{'conflict-handling recall':<34}{b_recall:>11.0%}{c_recall:>13.0%}")
    print(f"{'false-positive rate (lower better)':<34}{b_fpr:>11.0%}{c_fpr:>13.0%}")
    print("=" * 60)
    print(f"Planted conflicts: {nc}   Consistent questions: {ns}")
    print("Recall = flagged/resolved instead of silently answering one side.")


if __name__ == "__main__":
    main()
