from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import search

app = FastAPI(
    title="Fashion Rec API",
    description="Vector search API for fashion product recommendations",
    version="1.0.0"
)

# Allow the Vite dev server (frontend/) to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    # Any local port: Vite falls back to 5174, 5175... when 5173 is taken.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the search endpoint
app.include_router(search.router, prefix="/api/v1")

@app.get("/")
def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "ok", "message": "Fashion Rec API is running"}
