from app.config import settings
from app.store import get_collection


def retrieve(question: str, top_k: int | None = None) -> list[dict]:
    """Find the chunks most relevant to a question.
    Returns [{text, title, page, source, score}], score 0-1 (higher = closer).
    """
    k = top_k or settings.top_k
    collection = get_collection()

    results = collection.query(
        query_texts=[question],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # Chroma returns a list-per-query; we sent one query, so take index [0].
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    hits = []
    for text, meta, dist in zip(docs, metas, dists):
        hits.append({
            "text": text,
            "title": meta.get("title", "Unknown"),
            "page": meta.get("page"),
            "source": meta.get("source"),
            "score": round(1 - dist, 3),   # distance → similarity (higher = more relevant)
        })
    return hits