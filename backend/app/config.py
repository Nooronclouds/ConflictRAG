from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# BASE_DIR = the backend/ folder.
# __file__ is this file (app/config.py); .parent = app/, .parent.parent = backend/
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # --- Where things live on disk ---
    data_dir: Path = BASE_DIR / "data"
    upload_dir: Path = BASE_DIR / "data" / "uploads"   # PDFs we upload land here
    chroma_dir: Path = BASE_DIR / "data" / "chroma"    # the vector database lives here

    # --- Models ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # tiny, CPU, turns text->vectors
    ollama_url: str = "http://localhost:11434"          # where Ollama listens (its default)
    ollama_model: str = "llama3.2:3b"                   # the LLM that writes answers

    # --- Retrieval / chunking knobs ---
    chunk_size: int = 800        # characters per chunk of a document
    chunk_overlap: int = 120     # characters shared between neighbouring chunks (keeps context intact)
    top_k: int = 4               # how many chunks to fetch per question
    collection_name: str = "conflictrag"  # name of the table inside ChromaDB

    # Lets you override any value above via a .env file later, without editing this code
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# One shared settings object the whole app imports
settings = Settings()

# Create the data folders the moment config loads, so nothing later crashes on a missing folder
for _p in (settings.data_dir, settings.upload_dir, settings.chroma_dir):
    _p.mkdir(parents=True, exist_ok=True)