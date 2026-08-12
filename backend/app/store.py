#sets up the vector database and the embedding model.
import chromadb
from chromadb.utils import embedding_functions
from app.config import settings

# A persistent Chroma client: it saves the vector database to disk at
# settings.chroma_dir, so your knowledge base survives restarts.
_client = chromadb.PersistentClient(path=str(settings.chroma_dir))

# The embedding function turns text into vectors using the local MiniLM model.
# Chroma calls this automatically whenever we ADD or SEARCH text.
_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=settings.embedding_model
)


def get_collection():
    """Return the one shared collection (like a table) that holds every chunk."""
    return _client.get_or_create_collection(
        name=settings.collection_name,
        embedding_function=_embedding_fn,
        metadata={"hnsw:space": "cosine"},  # similarity measured by cosine distance
    )