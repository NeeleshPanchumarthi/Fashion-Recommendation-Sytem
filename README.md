# Fashion Search Service

A semantic fashion product search microservice. It turns a natural-language
query ("I need a dress for a wedding") into ranked products using query
understanding, vector retrieval over Pinecone and cross-encoder reranking.

The service owns one business capability, **product search**, and the
vector index that powers it. It runs as two separate processes from one
codebase:

| Process | Entry point | Lifecycle |
|---|---|---|
| **API** | `uvicorn app.main:app` | Long-running, serves requests |
| **Ingestion worker** | `python -m workers.ingestion_worker` | Offline batch job, resumable, fills the index |

The React app in `frontend/` is a separate client of this API.

## Architecture

```
Client ─► FastAPI (app/main.py: request IDs, errors, CORS)
            └─► api/v1 routers ─► services ─► retrieval ─► repositories ─► clients ─► Pinecone / Groq / models

Dataset ─► workers/ingestion_worker ─► batch_processor ─► services ─► repositories ─► Pinecone
```

```
app/
  main.py            app factory, startup (model warm-up), middleware, error handling
  dependencies.py    composition root: builds clients → repositories → services
  api/               HTTP only: router.py, v1/health.py, v1/search.py
  core/              config.py, logging.py, exceptions.py
  schemas/           HTTP request/response contracts
  domain/            Product, SearchFilters, image-selection rule, attribute vocabularies/extractors
  services/          use cases: search, health/readiness, review analysis, product enrichment
  retrieval/         query processing, retriever (gender pools, relaxation), reranker, pipeline
  repositories/      vector_repository (Pinecone schema + filters), dataset_repository (parquet/DuckDB)
  clients/           Pinecone, Groq LLM, embedding, cross-encoder and sentiment models
workers/             ingestion_worker (CLI + loop), batch_processor, checkpoint_manager
scripts/             convert_dataset, check_pinecone, generate_sample_data
tests/unit/          fast tests with in-memory fakes (no network)
tests/integration/   API over HTTP, worker end-to-end, live Pinecone (opt-in)
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Liveness: process is up |
| GET | `/api/v1/ready` | Readiness: models loaded, Pinecone reachable (503 if not) |
| POST | `/api/v1/search` | `{"query": "...", "top_k": 10}` → ranked products |

Errors return `{"detail", "code", "request_id"}`: 400 invalid request,
422 validation error, 503 dependency unavailable, 500 internal error. Every
response has an `X-Request-ID` header, which also appears in the logs.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows; use `source .venv/bin/activate` elsewhere
pip install -r requirements-dev.txt
cp .env.example .env            # then set PINECONE_API_KEY (and GROQ_API_KEY, optional)
```

## Running

```bash
# API (http://127.0.0.1:8000/docs)
uvicorn app.main:app --reload

# Ingestion worker
python -m workers.ingestion_worker --dry-run          # count batches only
python -m workers.ingestion_worker --max-batches 2    # small real run
python -m workers.ingestion_worker                    # full run; Ctrl-C safe, rerun to resume
python -m workers.ingestion_worker --only-failed      # retry failed batches

# Tests
pytest                                    # unit + integration (no network)
RUN_LIVE_TESTS=1 pytest tests/integration/vector_db   # against the real index
```

The worker reads `data/metadata.parquet` and `data/reviews.parquet` and
checkpoints to `data/checkpoints/`. Only one batch of reviews is held in
memory at a time.

## Configuration

All settings come from environment variables or `.env`; see `.env.example`.
Only `PINECONE_API_KEY` is required. Without `GROQ_API_KEY`, query
understanding falls back to regex extraction.
