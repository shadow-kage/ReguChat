# ReguChat

ReguChat is a **compliance-aware, domain-specific conversational AI system**. It answers natural-language queries against curated document knowledge bases using Retrieval-Augmented Generation (RAG). New knowledge domains can be added without changing any code — each domain is a single YAML configuration file pointing at a folder of source documents.

## How it works

1. An offline **indexer** reads source PDFs, splits them into chunks, embeds them with a local sentence-transformer model, and writes a FAISS vector index to disk.
2. At runtime, the **API server** loads all configured domain indexes into memory. When a query arrives, it embeds the query, retrieves the top-k most relevant chunks from the target domain, and passes them to an LLM (Gemini → Groq fallback) to generate a concise, grounded answer.
3. Answers are cached in Redis by a normalised query key so repeated queries skip the LLM entirely.

---

## Project structure

```
reguchat/
├── Dockerfile                     # Single image for both api and indexer services
├── docker-compose.yml             # Orchestration: redis + api + on-demand indexer
├── pyproject.toml                 # Project metadata and all Python dependencies
├── .env.example                   # Environment variable template
├── .gitignore
├── README.md
│
├── domains/                       # Domain configuration files (committed to git)
│   └── medical.yaml               # System prompt, noise filters, retrieval params, paths
│
├── data/                          # Source PDFs organised per domain (gitignored)
│   └── medical/
│       └── *.pdf
│
├── indexes/                       # Built FAISS artifacts per domain (gitignored)
│   └── medical/
│       ├── index.faiss
│       └── chunks.pkl
│
└── app/
    ├── main.py                    # FastAPI app entry point; lifespan loads all domains
    ├── config.py                  # Typed settings via pydantic-settings, reads .env
    ├── domain.py                  # DomainPack dataclass + DomainRegistry singleton
    │
    ├── api/
    │   ├── routes.py              # HTTP endpoints — thin handlers that delegate to services
    │   └── schemas.py             # Pydantic request/response models
    │
    ├── core/
    │   ├── embeddings.py          # SentenceTransformer singleton; GPU-aware + OOM recovery
    │   ├── faiss_store.py         # FAISSVectorDB wrapper: add, search, save, load
    │   └── markers.py             # Unicode status symbols for indexer CLI output
    │
    ├── services/
    │   ├── answer.py              # Full RAG pipeline: cache check → retrieve → LLM → cache
    │   ├── cache.py               # Async Redis with domain-namespaced keys; graceful on failure
    │   ├── llm.py                 # Gemini → Groq → rule-based cascade; streaming-aware
    │   └── retrieval.py           # FAISS top-k search filtered by relevance threshold
    │
    └── indexer/
        ├── build.py               # CLI: python -m app.indexer.build <domain.yaml>
        ├── chunking.py            # RecursiveCharacterTextSplitter (2000 chars, 200 overlap)
        └── extraction.py          # Parallel PDF text extraction via PyMuPDF
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Server status and list of loaded domain IDs |
| `GET` | `/domains` | All configured domains (id, name, description) |
| `GET` | `/domains/{domain_id}` | Single domain info |
| `POST` | `/query` | RAG query — returns a JSON response |
| `POST` | `/query/stream` | RAG query — returns an SSE stream |

**Request body** for `/query` and `/query/stream`:

```json
{
  "query": "What is tuberculosis?",
  "domain_id": "medical"
}
```

**Response** for `/query`:

```json
{
  "answer": "Tuberculosis (TB) is a bacterial infection...",
  "domain_id": "medical",
  "cached": false,
  "is_fallback": false
}
```

Interactive docs available at **`/docs`** when the server is running.

---

## Running from scratch

### Prerequisites

- Python 3.11+
- Docker Desktop (for Redis; also needed for full containerised deployment)
- [Gemini API key](https://aistudio.google.com/app/apikey)
- [Groq API key](https://console.groq.com/keys)
- [Hugging Face token](https://huggingface.co/settings/tokens) (for downloading the embedding model)

### 1. Clone and configure

```bash
git clone <repo-url>
cd reguchat
cp .env.example .env
```

Open `.env` and fill in:

```
HF_TOKEN=hf_...
GEMINI_API_KEY=...
GROQ_API_KEY=...
```

### 2. Set up the Python environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install .
```

### 3. Add source documents

Create `data/medical/` and place PDF files inside it:

```
data/
└── medical/
    ├── guideline-001.pdf
    └── ...
```

### 4. Build the index

Run once (or whenever source documents change):

```bash
python -m app.indexer.build domains/medical.yaml
```

Writes `indexes/medical/index.faiss` and `indexes/medical/chunks.pkl`.

### 5. Start Redis

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 6. Start the API server

```bash
uvicorn app.main:app --reload --port 8000
```

The startup log will confirm which domains loaded and how many vectors each holds.

### 7. Test

```bash
# Health check
curl http://localhost:8000/health

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is tuberculosis?", "domain_id": "medical"}'

# SSE stream
curl -N -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is tuberculosis?", "domain_id": "medical"}'
```

---

## Full Docker deployment (optional)

The indexer needs to run before the API so the FAISS index exists on disk.

```bash
# Build the shared image
docker compose build

# Index the medical domain (one-time; writes to ./indexes/medical/)
docker compose --profile indexer run --rm indexer domains/medical.yaml

# Start redis + api
docker compose up
```

---

## Adding a new domain

1. Create `domains/<name>.yaml` — copy `medical.yaml` as a template
2. Set `pdf_folder`, `vector_db_path`, and the domain-specific `system_prompt`
3. Place source PDFs in the folder referenced by `pdf_folder`
4. Run the indexer: `python -m app.indexer.build domains/<name>.yaml`
5. Restart the API server — the new domain loads automatically

No code changes required.
