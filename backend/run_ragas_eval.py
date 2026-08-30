"""
Phase 5 — answer-quality evaluation (baseline RAG vs ConflictRAG).

Everything runs LOCALLY (privacy preserved). Two complementary metrics:

  - faithfulness      : is every sentence of the answer supported by the
                        retrieved context? Computed with the project's own
                        DeBERTa NLI model (entailment) — deterministic and
                        reliable. RAGAS's LLM-based faithfulness returns NaN
                        with a small local judge, so we use our NLI instead
                        (this is exactly RAGAS's definition of faithfulness).

  - answer_relevancy  : does the answer actually address the question?
                        Scored by RAGAS with a local Ollama judge (llama3.1:8b)
                        + nomic-embed-text embeddings.

Run:
    cd conflictRAG/backend
    .venv\\Scripts\\activate
    pip install "ragas==0.1.21" langchain-ollama langchain-community datasets
    python run_ragas_eval.py
"""
import re
import warnings
warnings.filterwarnings("ignore")

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy
from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.retrieve import retrieve
from app.pipeline import answer_question
from app.nli import check_pair
from app.config import settings

JUDGE_MODEL = "llama3.1:8b"
EMBED_MODEL = "nomic-embed-text"
TOP_K = settings.top_k

# Edit / extend. Pick questions your KB can actually answer; the last is a
# deliberate conflict case (baseline blends, ConflictRAG handles it).
QUESTIONS = [
    "What is retrieval-augmented generation?",
    "What are knowledge conflicts in large language models?",
    "What causes hallucination in large language models?",
    "How does retrieval help language models stay factual?",
    "What is a knowledge-intensive NLP task?",
    "What are the limitations of large language models?",
    "How many days per week must employees be in the office?",   # conflict case
]


def contexts_for(question: str) -> list[str]:
    return [h["text"] for h in retrieve(question, top_k=TOP_K)]


def answer_text(res: dict) -> str:
    """Flatten the pipeline's typed response into a single answer string."""
    t = res.get("type")
    if t in ("confident", "resolved"):
        return res.get("answer", "")
    if t == "conflict":
        srcs = "; ".join(f'{s["doc"]}: {s["excerpt"]}' for s in res.get("sources", []))
        return f'{res.get("suggestion", "")} Sources: {srcs}'
    return res.get("message", "")   # not_found


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 12]


def faithfulness_nli(answer: str, contexts: list[str]) -> float | None:
    """Fraction of answer sentences ENTAILED by at least one retrieved chunk.
    Uses the project's DeBERTa NLI (premise = chunk, hypothesis = sentence)."""
    sents = _sentences(answer)
    if not sents or not contexts:
        return None
    supported = 0
    for s in sents:
        if any(check_pair(c, s)["label"] == "entailment" for c in contexts):
            supported += 1
    return supported / len(sents)


def build_rows(mode: str) -> list[dict]:
    rows = []
    for q in QUESTIONS:
        ctx = contexts_for(q)
        ans = answer_text(answer_question(q, mode=mode))
        if not ans or not ctx:
            print(f"   [skip] {mode}: no answer/context for {q!r}")
            continue
        rows.append({"question": q, "answer": ans, "contexts": ctx})
    return rows


def score_mode(mode: str, llm, emb) -> dict:
    print(f"\n>>> Scoring mode = {mode} ...")
    rows = build_rows(mode)

    # faithfulness — local NLI, one score per row
    faith = [faithfulness_nli(r["answer"], r["contexts"]) for r in rows]
    faith = [f for f in faith if f is not None]
    faithfulness = sum(faith) / len(faith) if faith else float("nan")

    # answer relevancy — RAGAS with the local judge
    ds = Dataset.from_list(rows)
    ragas_res = evaluate(ds, metrics=[answer_relevancy], llm=llm, embeddings=emb,
                         raise_exceptions=False)
    relevancy = float(ragas_res["answer_relevancy"])

    return {"n": len(rows), "faithfulness": faithfulness, "answer_relevancy": relevancy}


def main():
    llm = ChatOllama(model=JUDGE_MODEL, temperature=0)
    emb = OllamaEmbeddings(model=EMBED_MODEL)

    baseline = score_mode("baseline", llm, emb)
    conflictrag = score_mode("conflictrag", llm, emb)

    print("\n" + "=" * 64)
    print(f"{'metric':<22}{'baseline':>12}{'conflictrag':>14}{'Δ':>10}")
    print("-" * 64)
    for m in ("faithfulness", "answer_relevancy"):
        b, c = baseline[m], conflictrag[m]
        print(f"{m:<22}{b:>12.3f}{c:>14.3f}{c - b:>+10.3f}")
    print("-" * 64)
    print(f"{'questions scored':<22}{baseline['n']:>12}{conflictrag['n']:>14}")
    print("=" * 64)
    print("Higher is better. Δ = conflictrag − baseline.")
    print("faithfulness = NLI-entailed answer sentences; relevancy = RAGAS (local judge).")


if __name__ == "__main__":
    main()
