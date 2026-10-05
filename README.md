<div align="center">

# 👗 StyleIQ: Semantic Fashion Search & Virtual Try-On

**Describe what you want to wear. Find it, see it on yourself, and get the whole look.**

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Pinecone](https://img.shields.io/badge/Vector%20DB-Pinecone-000000)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)

</div>

---

## Table of Contents
1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Demo](#demo)
4. [Architecture](#architecture)
5. [Tech Stack](#tech-stack)
6. [Project Structure](#project-structure)
7. [Getting Started](#getting-started)
8. [API Reference](#api-reference)
9. [Configuration](#configuration)
10. [Testing](#testing)
11. [Production Scale Considerations](#production-scale-considerations)
12. [Additional Exploration](#additional-exploration)

---

## Overview

StyleIQ is a semantic fashion search microservice. It turns a natural-language request such as *"I need a dress for a wedding"* into ranked, relevant products. It does this through query understanding, vector retrieval over Pinecone, and cross-encoder reranking.

The system has two decoupled processes built from one codebase:

| Process | Entry point | Role |
|---|---|---|
| **API** | `uvicorn app.main:app` | Long-running service that handles search and try-on requests |
| **Ingestion worker** | `python -m workers.ingestion_worker` | Resumable offline batch job that builds the vector index |

A React frontend in `frontend/` is a separate client of the API.

## Key Features

- **Semantic search:** understands intent and occasion rather than only keywords.
- **Hybrid query understanding:** regex extraction first, with an LLM (Groq) filling the gaps.
- **Two-stage retrieval:** dense vector search, then a cross-encoder reranker for precision.
- **Outfit-aware search:** general requests such as *"an outfit for a party"* return a complete look across tops, bottoms, footwear, and accessories.
- **Review intelligence:** review scoring and sentiment analysis are computed at ingestion and shown as product insights.
- **Virtual try-on:** preview a garment on your own photo through an asynchronous job flow.
- **Resilient ingestion:** memory-bounded batches, checkpointing, retry of failed batches, and safe interruption with Ctrl-C.
- **Operational readiness:** liveness and readiness probes, request IDs on every response, and structured error contracts.

## Demo


<!-- DEMO_PLACEHOLDER -->
<p align="center">
  <img src="docs/Appdemo.gif"
       alt="Fashion Recommendation Demo"
       width="900">
</p>

## Architecture



<!-- ARCHITECTURE_DIAGRAM_PLACEHOLDER -->

<p align="center">
  <img src="docs/architecture-diagram.png" alt="Architecture Diagram" width="900">
</p>

**Search flow.** The query is understood, embedded in one batch, and searched in Pinecone once per gender pool (and per outfit group for outfit queries, in parallel). Results are reranked in a single cross-encoder batch, interleaved, and cut to `top_k`.

**Try-on flow.** `POST` validates the photo and garment URL and returns a job immediately (`202`). A background worker thread calls the Hugging Face Space. The client polls `GET` for the stage and the final image. Jobs are kept in memory for 15 minutes, and uploaded photos are never stored.

Pinecone is the only runtime handoff between the API and the ingestion worker. Full detail is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.13, FastAPI, Pydantic, Uvicorn |
| **Retrieval** | Pinecone, Sentence-Transformers (`all-MiniLM-L6-v2`), Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) |
| **LLM** | Groq (`openai/gpt-oss-120b`) for query understanding |
| **Reviews** | `nlptown/bert-base-multilingual-uncased-sentiment` |
| **Virtual try-on** | Leffa on a Hugging Face Space (`gradio_client`) |
| **Data** | Parquet, DuckDB, Pandas |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS 4, Radix UI |
| **Testing** | Pytest |

## Project Structure

```text
app/
  main.py            App factory, startup model warm-up, middleware, error handling
  dependencies.py    Composition root (clients → repositories → services)
  api/               HTTP layer: health, search, try-on routes
  core/              Configuration, logging, exceptions
  schemas/           Request/response contracts
  domain/            Product, filters, outfit rules, attribute extractors
  services/          Use cases: search, health, review analysis, enrichment
  retrieval/         Query processing, retriever, reranker, pipeline
  repositories/      Pinecone access, parquet/DuckDB dataset access
  clients/           Pinecone, Groq, embedding, reranker, sentiment, try-on
workers/             Ingestion CLI, batch processor, checkpoint manager
scripts/             Dataset conversion, index checks, sample data
tests/               Unit (in-memory fakes) and integration tests
frontend/            React + Vite client
docs/                Architecture documentation
```

The code follows a layered design: routes handle HTTP only, services own use cases, repositories isolate data stores, and clients wrap external systems.

## Getting Started

### Prerequisites
- Python 3.13
- Node.js 20+ (for the frontend)
- A [Pinecone](https://www.pinecone.io/) API key
- A [Groq](https://console.groq.com/) API key (LLM query understanding)
- A [Hugging Face](https://huggingface.co/settings/tokens) "Read" token (virtual try-on)

### 1. Backend setup
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # then set PINECONE_API_KEY, GROQ_API_KEY and HF_TOKEN
```

### 2. Build the search index
```bash
python -m workers.ingestion_worker --dry-run          # count batches only
python -m workers.ingestion_worker --max-batches 2    # small trial run
python -m workers.ingestion_worker                    # full run (Ctrl-C safe, rerun to resume)
python -m workers.ingestion_worker --only-failed      # retry failed batches
```
The worker reads `data/metadata.parquet` and `data/reviews.parquet`, checkpoints progress to `data/checkpoints/`, and holds only one batch in memory at a time.

### 3. Run the API
```bash
uvicorn app.main:app --reload
```
Interactive docs are at `http://127.0.0.1:8000/docs`.

### 4. Run the frontend
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness check |
| `GET` | `/api/ready` | Readiness check (models loaded, Pinecone reachable) |
| `POST` | `/api/search` | `{"query": "...", "top_k": 10}` returns ranked products |
| `POST` | `/api/try-on` | Multipart `person_image`, `garment_image_url`, `garment_type`. Returns `202` with a job |
| `GET` | `/api/try-on/{job_id}` | Poll the job for `stage`, `queue_position`, and `result_image` |

**Error contract.** Errors return `{"detail", "code", "request_id"}` with these status codes: `400` invalid request, `422` validation error, `429` too many try-ons, `503` dependency unavailable, `500` internal error. Every response carries an `X-Request-ID` header, which also appears in the logs.

## Configuration

All settings come from environment variables or `.env` (see `.env.example`). `PINECONE_API_KEY`, `GROQ_API_KEY` and `HF_TOKEN` are required.

| Variable | Purpose | Default |
|---|---|---|
| `PINECONE_API_KEY` | Vector database access | *required* |
| `GROQ_API_KEY` | LLM query understanding | *required* |
| `HF_TOKEN` | Hugging Face access for virtual try-on | *required* |
| `PINECONE_INDEX` | Index name | `fashionvectors` |
| `EMBEDDING_MODEL` | Bi-encoder for retrieval | `all-MiniLM-L6-v2` |
| `CROSS_ENCODER_MODEL` | Reranker | `ms-marco-MiniLM-L-6-v2` |
| `TOP_K` / `DENSE_SEARCH_K` | Result size / candidate pool | `36` / `60` |
| `TRYON_MAX_ACTIVE_JOBS` | Concurrent try-on limit | `4` |
| `BATCH_SIZE` | Ingestion batch size | `15000` |

## Testing

```bash
pytest                                                # unit + integration, no network required
RUN_LIVE_TESTS=1 pytest tests/integration/vector_db   # against the live Pinecone index
```

---

## Production Scale Considerations

The current prototype is functionally complete. Moving it to production scale calls for improvements in five areas: infrastructure, state management, retrieval quality, data quality, and observability.

### 1. Containerization, Orchestration, and CI/CD
Package the API, ingestion worker, and frontend as separate container images. Deploy them on a managed orchestration platform such as Kubernetes, Google Cloud Run, or AWS ECS. Each service scales horizontally and independently, with replica counts adjusted automatically to demand. Use GitHub Actions to automate build, test, image publishing, and deployment, so every change is validated and released through a repeatable pipeline.

### 2. Distributed Job Queue and Caching with Redis
Try-on jobs are currently held in process memory. Move them to a durable queue backed by Redis, using ARQ or Celery. This makes the API tier stateless, so any replica can accept a request and any worker can process it, and jobs survive restarts and scale-outs. Use Redis as a cache for frequent queries and computed embeddings. This lowers latency, reduces load on downstream services, and cuts the cost of repeated inference.

### 3. Upgraded Embedding Model and Reranking
Replace the current embedding model with a higher-capacity one, either `bge-large-en-v1.5` or OpenAI `text-embedding-3`. Add a second-stage cross-encoder reranker, `bge-reranker-v2-m3`, to refine the top candidates. Serve both models as independent inference services through Hugging Face Text Embeddings Inference (TEI), so they scale separately from the application. Re-ingest the catalog into a new Pinecone index sized for the new embedding dimensions. The old index stays in service until the new one is validated, which allows a safe cutover and rollback.

### 4. Data Quality and LLM-Based Review Enrichment
Improve catalog quality by normalizing product categories into a consistent taxonomy and removing duplicate products. Replace the BERT sentiment classifier with an LLM, such as Claude Haiku or Llama 3.3 70B, that extracts structured aspects from reviews, including fit, sizing, and fabric. Run this extraction offline in the ingestion worker, so it adds no latency to user requests. Append the extracted aspects to the text that gets embedded, so retrieval can match shopper intent more precisely (for example, "runs small" or "soft fabric").

### 5. Evaluation Framework and Observability
Build a labeled relevance dataset and use it to measure retrieval quality with nDCG@10 and Recall@K. Run these metrics as a regression gate before releasing any change to the models, index, or ranking logic. For runtime visibility, add:
- **OpenTelemetry** for distributed tracing across services.
- **Prometheus and Grafana** for metrics and dashboards.
- **Sentry** for error tracking and alerting.

As a longer-term enhancement, fine-tune a small language model with LoRA on domain-specific data and serve it with vLLM. This would lower inference cost and improve domain relevance.

## Additional Exploration

Beyond the core search and recommendation pipeline, the following capabilities extend the product from single-item discovery to complete styling assistance.

### 1. Virtual Try-On (Implemented)
The virtual try-on feature is already implemented. Shoppers can preview a selected garment on their own photo before purchase, which helps them judge fit and appearance. Next steps are to improve output fidelity and reduce generation latency. These build on the production work described above: the asynchronous job queue and horizontally scaled workers.

### 2. Complete Outfit Recommendation
Extend the recommender from single products to full outfits, such as shirt, pant, shoes, and accessories. Given a shopper's query, occasion, or anchor item, the system would assemble a coordinated set from across product categories. The approach would combine:
- **Category-aware retrieval:** fetch candidates for each outfit slot (top, bottom, footwear, accessories) separately from the vector index.
- **Compatibility scoring:** rank candidate combinations on color harmony, style and formality consistency, season, and price range, rather than on similarity to the query alone.
- **Bundle presentation:** return the outfit as a single set that can be previewed with the try-on feature and added to the cart together.

### 3. Complementary Item Matching
Support targeted pairing from a single anchor item:
- A matching shirt for a given pant, or a matching pant for a given shirt.
- Matching shoes for a given shirt and pant combination.

This relies on a compatibility model that captures which items work well together. Options include:
- Embedding-based similarity on style attributes, combined with rules for color and formality.
- Learning compatibility from co-purchase and co-view behavior.
- Using an LLM to reason over item attributes and explain each pairing, such as "navy chinos pair well with this white oxford shirt".

The structured category taxonomy and extracted attributes from the data-quality work in the previous section are prerequisites. They give the matching logic clean, comparable features to work with.

---

## License
*To be added.*
