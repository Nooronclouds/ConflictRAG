from app.config import settings
from app.store import get_collection


def retrieve(question: str, top_k: int | None = None, source: str | None = None) -> list[dict]:
    """Find the chunks most relevant to a question.
    Returns [{text, title, page, source, score}], score 0-1 (higher = closer).
    If `source` is given, only search chunks from that one document.
    """
    k = top_k or settings.top_k
    collection = get_collection()

    # Over-fetch, then de-duplicate: the same document may have been ingested more
    # than once, so identical chunks come back repeated and waste the top-k slots.
    results = collection.query(
        query_texts=[question],
        n_results=k * 4,
        include=["documents", "metadatas", "distances"],
        where={"source": source} if source else None,
    )

    # Chroma returns a list-per-query; we sent one query, so take index [0].
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    hits, seen = [], set()
    for text, meta, dist in zip(docs, metas, dists):
        key = (meta.get("source"), meta.get("page"), text[:120])
        if key in seen:
            continue
        seen.add(key)
        hits.append({
            "text": text,
            "title": meta.get("title", "Unknown"),
            "page": meta.get("page"),
            "source": meta.get("source"),
            "score": round(1 - dist, 3),   # distance → similarity (higher = more relevant)
        })
        if len(hits) >= k:
            break
    return hits