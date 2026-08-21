import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent          # folder holding the three input files
FILES = ["conflictbank_subset.jsonl", "planted_conflicts.jsonl", "negatives.jsonl"]
OUTPUT = DATA_DIR / "eval_dataset.jsonl"

CORE_FIELDS = {"original", "conflicting", "conflict_type", "label", "source"}
VALID_LABELS = {"conflict", "no_conflict"}
VALID_CONFLICT_TYPES = {"factual", "temporal", "contradictory"}


def load_rows(path):
    rows = []
    if not path.exists():
        print(f"  MISSING: {path.name}")
        return rows
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"  BAD JSON in {path.name} line {i}")
    return rows


def validate(row, where):
    errs = []
    if not CORE_FIELDS.issubset(row):
        return [f"{where}: missing fields {CORE_FIELDS - set(row)}"]
    if row["label"] not in VALID_LABELS:
        errs.append(f"{where}: bad label {row['label']!r}")
    if row["label"] == "conflict" and row["conflict_type"] not in VALID_CONFLICT_TYPES:
        errs.append(f"{where}: conflict row has bad conflict_type {row['conflict_type']!r}")
    if row["label"] == "no_conflict" and row["conflict_type"] != "none":
        errs.append(f"{where}: no_conflict should have conflict_type 'none', got {row['conflict_type']!r}")
    if not str(row["original"]).strip() or not str(row["conflicting"]).strip():
        errs.append(f"{where}: empty original/conflicting")
    return errs


all_rows, all_errs = [], []
print("Loading files:")
for name in FILES:
    rows = load_rows(DATA_DIR / name)
    print(f"  {name}: {len(rows)} rows")
    for i, row in enumerate(rows):
        row.setdefault("subtype", "none")          # add subtype where missing
        all_errs += validate(row, f"{name}[{i}]")
        all_rows.append(row)

print("\n--- VALIDATION ---")
if all_errs:
    print(f"  {len(all_errs)} problems (first 10):")
    for e in all_errs[:10]:
        print("   -", e)
else:
    print("  OK — no schema problems")

labels = Counter(r["label"] for r in all_rows)
conflict_types = Counter(r["conflict_type"] for r in all_rows if r["label"] == "conflict")
sources = Counter(r["source"] for r in all_rows)
neg_subtypes = Counter(r["subtype"] for r in all_rows if r["label"] == "no_conflict")

print("\n--- COMPOSITION ---")
print("  total rows      :", len(all_rows))
print("  by label        :", dict(labels))
print("  conflict types  :", dict(conflict_types))
print("  by source       :", dict(sources))
print("  negative subtype:", dict(neg_subtypes))
hard = sum(v for k, v in neg_subtypes.items() if k in {"paraphrase", "same_domain"})
neg_total = labels.get("no_conflict", 0)
if neg_total:
    print(f"  hard negatives  : {hard}/{neg_total} ({round(100*hard/neg_total)}%)")

if all_errs:
    print("\nFix the problems above, then re-run. Nothing written.")
else:
    with OUTPUT.open("w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(all_rows)} rows to {OUTPUT.name}")