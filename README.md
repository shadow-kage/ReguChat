# ReguChat

ReguChat is a **compliance-aware, domain-specific conversational AI system**. It answers natural-language queries against curated document knowledge bases using Retrieval-Augmented Generation (RAG). New knowledge domains can be added without changing any code — each domain is a single YAML configuration file pointing at a folder of source documents.

## How it works

1. An offline **indexer** reads source PDFs, splits them into chunks, embeds them with a local sentence-transformer model, and writes a FAISS vector index to disk.
2. At runtime, the **API server** loads all configured domain indexes into memory. When a query arrives, it embeds the query, retrieves the top-k most relevant chunks from the target domain, and passes them to an LLM (Gemini → Groq fallback) to generate a concise, grounded answer.
3. Answers are cached in Redis by a normalised query key so repeated queries skip the LLM entirely.
4. The **frontend** is a React SPA with an open-book layout — left page shows domain info, right page holds the chat.

---

## Project structure

```
reguchat/
├── docker-compose.yml             # Orchestration: redis + backend + frontend + on-demand indexer
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
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml             # All Python dependencies; replaces requirements.txt
│   └── app/
│       ├── main.py                # FastAPI app entry point; lifespan loads all domains
│       ├── config.py              # Typed settings via pydantic-settings, reads .env
│       ├── domain.py              # DomainPack dataclass + DomainRegistry singleton
│       │
│       ├── api/
│       │   ├── routes.py          # HTTP endpoints — thin handlers that delegate to services
│       │   └── schemas.py         # Pydantic request/response models
│       │
│       ├── core/
│       │   ├── embeddings.py      # SentenceTransformer singleton; GPU-aware + OOM recovery
│       │   ├── faiss_store.py     # FAISSVectorDB wrapper: add, search, save, load
│       │   └── markers.py         # Unicode status symbols for indexer CLI output
│       │
│       ├── services/
│       │   ├── answer.py          # Full RAG pipeline: cache check → retrieve → LLM → cache
│       │   ├── cache.py           # Async Redis with domain-namespaced keys; graceful on failure
│       │   ├── llm.py             # Gemini → Groq → rule-based cascade; streaming-aware
│       │   └── retrieval.py       # FAISS top-k search filtered by relevance threshold
│       │
│       └── indexer/
│           ├── build.py           # CLI: python -m app.indexer.build <domain.yaml>
│           ├── chunking.py        # RecursiveCharacterTextSplitter (2000 chars, 200 overlap)
│           └── extraction.py      # Parallel PDF text extraction via PyMuPDF
│
└── frontend/
    ├── Dockerfile                 # Multi-stage: node build → nginx serve
    ├── nginx.conf                 # Proxies /api/* to backend; SPA fallback
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts             # Dev server proxy strips /api prefix
    ├── index.html
    └── src/
        ├── main.tsx               # CSS imports + ReactDOM mount
        ├── App.tsx                # Fetches domains at mount; owns selected domain state
        ├── types.ts               # Shared TypeScript interfaces
        │
        ├── components/
        │   ├── Book.tsx           # Two-page CSS grid + spine shadow
        │   ├── LeftPage.tsx       # Logo, description, domain selector
        │   ├── RightPage.tsx      # Chat header, message stream, composer
        │   ├── ChatStream.tsx     # Auto-scrolling message list
        │   ├── MessageBubble.tsx  # User / bot / error bubble variants
        │   ├── StatusBadge.tsx    # Cache-hit (green) / cache-miss (amber) pill
        │   └── Composer.tsx       # Auto-grow textarea; Enter to send, Shift+Enter for newline
        │
        ├── hooks/
        │   └── useChat.ts         # useReducer state machine + SSE consumer
        │
        ├── lib/
        │   ├── api.ts             # Typed fetch wrappers for /health and /domains
        │   └── sse.ts             # fetch + ReadableStream → AsyncGenerator<SSEEvent>
        │
        └── styles/
            ├── tokens.css         # CSS custom properties (colours, fonts)
            ├── index.css          # Base reset
            ├── book.css           # Book layout, page shadows, spine, responsive stack
            └── chat.css           # Typography, bubbles, badges, composer
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

Interactive API docs are available at **`http://localhost:8000/docs`** when the server is running.

---

## Running locally (without Docker)

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (for Redis)
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

pip install ./backend
```

### 3. Add source documents

```
data/
└── medical/
    ├── guideline-001.pdf
    └── ...
```

### 4. Build the index

Run once (or whenever source documents change):

```bash
PYTHONPATH=backend python -m app.indexer.build domains/medical.yaml
```

Writes `indexes/medical/index.faiss` and `indexes/medical/chunks.pkl`.

### 5. Start Redis

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 6. Start the backend

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

Run from the project root so that `domains/` and `indexes/` resolve correctly.

### 7. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. The Vite dev proxy forwards all `/api/*` requests to `localhost:8000`, so no CORS configuration is needed.

### 8. Test the backend directly

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

## Full Docker deployment

The indexer must run before the API so the FAISS index exists on disk.

```bash
# Build all images
docker compose build

# Index the medical domain (one-time; writes to ./indexes/medical/)
docker compose --profile indexer run --rm indexer domains/medical.yaml

# Start redis + backend + frontend
docker compose up
```

Frontend is served at `http://localhost:5173`, backend at `http://localhost:8000`.

---

## Adding a new domain

1. Create `domains/<name>.yaml` — copy `medical.yaml` as a template
2. Set `pdf_folder`, `vector_db_path`, and the domain-specific `system_prompt`
3. Place source PDFs in the folder referenced by `pdf_folder`
4. Run the indexer: `PYTHONPATH=backend python -m app.indexer.build domains/<name>.yaml`
5. Restart the API server — the new domain loads automatically and appears in the frontend domain list
