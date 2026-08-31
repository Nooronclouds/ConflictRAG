"""
Phase 5 — answer-quality evaluation (baseline RAG vs ConflictRAG).

RAGAS-STYLE metrics computed FULLY LOCALLY and deterministically. We do NOT use
RAGAS's LLM judge: with a local privacy-preserving model it returns NaN
(faithfulness) and times out (relevancy). Instead we measure the same things
with the models the project already runs — no cloud, no network, reproducible:

  - faithfulness     : fraction of answer sentences ENTAILED by the retrieved
                       context, via the project's DeBERTa NLI model. This is
                       exactly RAGAS's definition of faithfulness (grounding).

  - answer_relevancy : cosine similarity between the question and the answer in
                       the local MiniLM embedding space (higher = the answer is
                       on-topic for the question).

Everything is offline: MiniLM + DeBERTa load from the local HuggingFace cache,
answers come from local Ollama. To guarantee zero network calls, first download
the models once, then set  HF_HUB_OFFLINE=1  and  TRANSFORMERS_OFFLINE=1 .

Run:
    cd conflictRAG/backend
    .venv\\Scripts\\activate
    python run_ragas_eval.py
"""
import re
import warnings
warnings.filterwarnings("ignore")

from sentence_transformers import SentenceTransformer, util

from app.retrieve import retrieve
from app.pipeline import answer_question
from app.nli import check_pair
from app.config import settings

TOP_K = settings.top_k
_embed = SentenceTransformer(settings.embedding_model)   # all-MiniLM-L6-v2, local

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
    """Fraction of answer sentences ENTAILED by at least one retrieved chunk."""
    sents = _sentences(answer)
    if not sents or not contexts:
        return None
    supported = sum(
        1 for s in sents
        if any(check_pair(c, s)["label"] == "entailment" for c in contexts)
    )
    return supported / len(sents)


def answer_relevancy(question: str, answer: str) -> float:
    """Cosine similarity of question and answer in the local embedding space."""
    qv = _embed.encode(question, convert_to_tensor=True, normalize_embeddings=True)
    av = _embed.encode(answer, convert_to_tensor=True, normalize_embeddings=True)
    return float(util.cos_sim(qv, av).item())


def score_mode(mode: str) -> dict:
    print(f"\n>>> Scoring mode = {mode} ...")
    faith, relev = [], []
    for q in QUESTIONS:
        ctx = contexts_for(q)
        ans = answer_text(answer_question(q, mode=mode))
        if not ans or not ctx:
            print(f"   [skip] no answer/context for {q!r}")
            continue
        f = faithfulness_nli(ans, ctx)
        if f is not None:
            faith.append(f)
        relev.append(answer_relevancy(q, ans))
        print(f"   [{mode}] faith={f:.2f} relev={relev[-1]:.2f}  {q}")
    return {
        "n": len(relev),
        "faithfulness": sum(faith) / len(faith) if faith else float("nan"),
        "answer_relevancy": sum(relev) / len(relev) if relev else float("nan"),
    }


def main():
    baseline = score_mode("baseline")
    conflictrag = score_mode("conflictrag")

    print("\n" + "=" * 64)
    print(f"{'metric':<22}{'baseline':>12}{'conflictrag':>14}{'delta':>10}")
    print("-" * 64)
    for m in ("faithfulness", "answer_relevancy"):
        b, c = baseline[m], conflictrag[m]
        print(f"{m:<22}{b:>12.3f}{c:>14.3f}{c - b:>+10.3f}")
    print("-" * 64)
    print(f"{'questions scored':<22}{baseline['n']:>12}{conflictrag['n']:>14}")
    print("=" * 64)
    print("Higher is better. delta = conflictrag - baseline.")
    print("faithfulness = NLI-entailed answer sentences; relevancy = embedding cosine.")


if __name__ == "__main__":
    main()
