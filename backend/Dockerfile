# ConflictRAG backend — FastAPI + CARL (DeBERTa NLI) + ChromaDB.
# The heavy LLM (Ollama) runs on the HOST; this image only needs CPU.
FROM python:3.11-slim

WORKDIR /app

# System deps: build tools for a couple of wheels; curl for the healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

# Python deps. sentencepiece is required by the DeBERTa-v3 tokenizer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt sentencepiece

# Bake the local models into the image so the container runs fully OFFLINE
# (no HuggingFace calls at runtime — matches the privacy guarantee).
ENV HF_HOME=/app/hf_cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); from transformers import AutoModelForSequenceClassification, AutoTokenizer; m='MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli'; AutoTokenizer.from_pretrained(m); AutoModelForSequenceClassification.from_pretrained(m); print('models baked')"

COPY app ./app

# Runtime config: talk to Ollama on the host; never phone home for models.
ENV OLLAMA_URL=http://host.docker.internal:11434 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD curl -fs http://localhost:8000/folders || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
