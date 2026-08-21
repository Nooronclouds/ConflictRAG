import json
from pathlib import Path
from collections import defaultdict
from app.nli import check_pair
from app.conflict import classify_conflict, CONFLICT_THRESHOLD

DATA = Path(__file__).parent.parent / "dataset" / "eval_dataset.jsonl"


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


rows = load(DATA)
print(f"Loaded {len(rows)} rows\n")

# 1) Score every pair with the NLI model ONCE (the expensive step).
print("Scoring pairs with NLI (one pass)...")
scored = []   # (row, contradiction_probability)
for i, row in enumerate(rows, 1):
    s = check_pair(row["original"], row["conflicting"])["scores"]["contradiction"]
    scored.append((row, s))
    if i % 100 == 0:
        print(f"  {i}/{len(rows)}")


def metrics(threshold):
    tp = fp = fn = tn = 0
    for row, s in scored:
        pred, truth = s >= threshold, row["label"] == "conflict"
        if pred and truth: tp += 1
        elif pred and not truth: fp += 1
        elif not pred and truth: fn += 1
        else: tn += 1
    p = tp/(tp+fp) if tp+fp else 0.0
    r = tp/(tp+fn) if tp+fn else 0.0
    f1 = 2*p*r/(p+r) if p+r else 0.0
    return p, r, f1, (tp+tn)/len(rows)


# 2) Threshold sweep — the precision/recall tradeoff (for tuning).
print("\n=== DETECTION: threshold sweep ===")
print(f"{'thresh':>7}{'prec':>8}{'recall':>8}{'f1':>7}{'acc':>7}")
for t in [0.5, 0.6, 0.7, 0.8, 0.9]:
    p, r, f1, a = metrics(t)
    print(f"{t:>7.2f}{p:>8.3f}{r:>8.3f}{f1:>7.3f}{a:>7.3f}")

# 3) Breakdown at the pipeline's default threshold.
T = CONFLICT_THRESHOLD
print(f"\n=== BREAKDOWN at default threshold {T} ===")
p, r, f1, a = metrics(T)
print(f"precision={p:.3f}  recall={r:.3f}  f1={f1:.3f}  accuracy={a:.3f}")

by_type = defaultdict(lambda: [0, 0])
for row, s in scored:
    if row["label"] == "conflict":
        by_type[row["conflict_type"]][1] += 1
        if s >= T: by_type[row["conflict_type"]][0] += 1
print("\nDetection rate (recall) by conflict type:")
for k, (d, tot) in by_type.items():
    print(f"  {k:15} {d}/{tot} ({d/tot:.1%})")

by_sub = defaultdict(lambda: [0, 0])
for row, s in scored:
    if row["label"] == "no_conflict":
        sub = row.get("subtype", "none")
        by_sub[sub][1] += 1
        if s >= T: by_sub[sub][0] += 1
print("\nFalse-alarm rate by negative subtype:")
for sub, (bad, tot) in by_sub.items():
    print(f"  {sub:15} {bad}/{tot} ({bad/tot:.1%})")

# 4) Conflict-type classification accuracy (on true conflicts).
print("\n=== CLASSIFICATION accuracy (type heuristic) ===")
correct = total = 0
per = defaultdict(lambda: [0, 0])
for row, s in scored:
    if row["label"] == "conflict":
        pred = classify_conflict(row["original"], row["conflicting"])
        total += 1
        per[row["conflict_type"]][1] += 1
        if pred == row["conflict_type"]:
            correct += 1
            per[row["conflict_type"]][0] += 1
print(f"Overall: {correct}/{total} ({correct/total:.1%})")
for k, (c, tot) in per.items():
    print(f"  {k:15} {c}/{tot} ({c/tot:.1%})")