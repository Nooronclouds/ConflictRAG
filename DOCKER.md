# Running ConflictRAG with Docker

One command brings up the **backend** (FastAPI + CARL) and **frontend** (React).
The LLM (**Ollama**) runs natively on the host so it can use the GPU directly;
everything else runs in containers and is fully offline.

The knowledge base starts **empty** on every new machine — you upload documents
from the UI.

## Prerequisites (on the host machine)

1. **Docker Desktop** (Windows/Mac) or Docker Engine + Compose (Linux).
2. **Ollama** installed and running: https://ollama.com
3. Pull the models Ollama serves:
   ```bash
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ```
   (Keep Ollama running — `ollama serve` / the tray app.)

## Start

From the `conflictRAG/` folder:
```bash
docker compose up --build
```
First build takes a while (it bakes the DeBERTa + MiniLM models into the image so
the container needs no internet at runtime). Then open:

- **App:**  http://localhost:5173
- **API docs:**  http://localhost:8000/docs

Upload a few PDFs from the UI and ask the Librarian questions.

## Stop / reset

```bash
docker compose down          # stop
rm -rf data/                 # wipe the knowledge base (optional; starts empty again)
```

## Notes

- The backend reaches Ollama at `host.docker.internal:11434`. If Ollama runs on a
  different host/port, change `OLLAMA_URL` in `docker-compose.yml`.
- No GPU is needed inside the containers (NLI + embeddings run on CPU). Ollama uses
  the host GPU if available.
- Everything is local: with the models baked in and `HF_HUB_OFFLINE=1`, the app
  makes no external network calls — you can run it with WiFi off.
