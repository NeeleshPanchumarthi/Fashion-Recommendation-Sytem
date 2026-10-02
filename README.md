# Project Files Overview

The following files have been added (or created) as part of the **Fashion Rec** project, listed in the order they were introduced, together with a brief reason for each:

| Order | File | Why it was created |
|------|------|--------------------|
| 1 | `requirements.txt` | Lists all Python dependencies (FastAPI, Pinecone, Sentence‑Transformers, etc.) required to run the pipeline and API. |
| 2 | `app/ingestion/pipeline.py` | Orchestrates the full ingestion flow – loads data, extracts attributes, processes sentiment, generates embeddings, and upserts vectors to Pinecone. |
| 3 | `app/ingestion/vector_store.py` | Provides Pinecone helper functions (`_get_index`, `upsert_vectors`, `query_vector`) using the new `pinecone` SDK. |
| 4 | `app/api/search.py` | FastAPI router exposing the **/search** endpoint that queries Pinecone and returns a typed `SearchResponseSchema`. |
| 5 | `app/main.py` | FastAPI application entry‑point – mounts the search router and adds a health‑check endpoint. |
| 6 | `generate_dummy_data.py` | Small utility script that creates a `data/` directory with dummy `metadata.parquet` and `reviews.parquet` files so the pipeline can run out‑of‑the‑box. |

---

## How to Run the Project

1. **Activate the virtual environment**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
2. **Install dependencies** (if you haven’t already)
   ```powershell
   pip install -r requirements.txt
   ```
3. **Generate sample data** (optional but required for the first run)
   ```powershell
   python generate_dummy_data.py
   ```
   This creates `data/metadata.parquet` and `data/reviews.parquet`.
4. **Run the ingestion pipeline** – this loads the data, extracts attributes, obtains LLM sentiment, embeds the texts and upserts them into Pinecone.
   ```powershell
   python -m app.ingestion.pipeline
   ```
5. **Start the FastAPI server**
   ```powershell
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000`. You can test the search endpoint, e.g.:
   ```bash
   curl -X POST "http://127.0.0.1:8000/api/v1/search" -H "Content-Type: application/json" -d '{"query": "red t‑shirt"}'
   ```

That’s it – you now have a fully‑functional ingestion pipeline and searchable API backed by Pinecone.
