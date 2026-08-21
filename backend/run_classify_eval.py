import json
from pathlib import Path
from collections import defaultdict
from app.conflict import classify_conflict

DATA = Path(__file__).parent.parent / "dataset" / "eval_dataset.jsonl"
rows = [json.loads(l) for l in open(DATA, encoding="utf-8") if l.strip()]
conflicts = [r for r in rows if r["label"] == "conflict"]

correct = 0
per_type = defaultdict(lambda: [0, 0])
per_source = defaultdict(lambda: [0, 0])
for r in conflicts:
    pred = classify_conflict(r["original"], r["conflicting"])
    hit = pred == r["conflict_type"]
    correct += hit
    per_type[r["conflict_type"]][1] += 1
    per_type[r["conflict_type"]][0] += hit
    per_source[r["source"]][1] += 1
    per_source[r["source"]][0] += hit

print(f"Overall: {correct}/{len(conflicts)} ({correct/len(conflicts):.1%})\n")
print("By type:")
for k, (c, t) in per_type.items():
    print(f"  {k:15} {c}/{t} ({c/t:.1%})")
print("\nBy source:")
for k, (c, t) in per_source.items():
    print(f"  {k:15} {c}/{t} ({c/t:.1%})")