"""One shared local sentence encoder (MiniLM), used for picking the claim
sentence most relevant to a question during conflict detection. Fully local."""
from sentence_transformers import SentenceTransformer
from app.config import settings

_model = SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]):
    """Return L2-normalised embeddings (numpy array, shape [n, d]); dot product
    of two rows is therefore their cosine similarity."""
    return _model.encode(texts, normalize_embeddings=True)
