from fastapi import FastAPI
from .api import search

app = FastAPI(
    title="Fashion Rec API",
    description="Vector search API for fashion product recommendations",
    version="1.0.0"
)

# Mount the search endpoint
app.include_router(search.router, prefix="/api/v1")

@app.get("/")
def health_check():
    """Health check endpoint to verify the API is running."""
    return {"status": "ok", "message": "Fashion Rec API is running"}
