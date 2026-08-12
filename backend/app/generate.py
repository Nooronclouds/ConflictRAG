import httpx
from app.config import settings

# The two experiment modes, as two system prompts:
BASELINE_PROMPT = (
    "You are a helpful assistant. Answer the question using the context provided."
)
CONFLICTRAG_PROMPT = (
    "You are a careful librarian. Answer ONLY using the provided context. "
    "If the context does not contain the answer, say you don't have a source for it. "
    "Be concise and factual, and mention which source you used."
)


def build_prompt(question: str, hits: list[dict], system_prompt: str) -> str:
    if hits:
        blocks = [f"[Source {i} — {h['title']}, p.{h['page']}]\n{h['text']}"
                  for i, h in enumerate(hits, start=1)]
        context = "\n\n".join(blocks)
    else:
        context = "(no documents found)"
    return f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"


def generate_answer(question: str, hits: list[dict], mode: str = "conflictrag") -> str:
    """Send question + context to the local LLM. mode = 'baseline' or 'conflictrag'."""
    system_prompt = CONFLICTRAG_PROMPT if mode == "conflictrag" else BASELINE_PROMPT
    prompt = build_prompt(question, hits, system_prompt)
    response = httpx.post(
        f"{settings.ollama_url}/api/generate",
        json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["response"].strip()