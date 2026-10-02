"""End‑to‑end ingestion pipeline.

* Loads product metadata and reviews.
* Extracts attributes (color, gender, size, style, category).
* Calls the LLM sentiment extractor for each review.
* Aggregates sentiment to the product level.
* Constructs a `combined_text` field that contains all searchable content.
* Generates embeddings with the Sentence‑Transformer model.
* Upserts the vectors (and full metadata) into Pinecone.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

from .data_loader import load_dataset
from .review_processor import process_reviews, aggregate_product_sentiment
from .attributes.color_extractor import extract_color
from .attributes.gender_extractor import extract_gender
from .attributes.size_extractor import extract_size
from .attributes.style_extractor import extract_style
from .attributes.category_extractor import extract_category
from .title_normalizer import normalize_title
from .embedding import embed_text
from .vector_store import upsert_vectors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _apply_attribute_extractors(df: pd.DataFrame) -> pd.DataFrame:
    """Run all rule‑based attribute extractors and add the results as new columns."""
    df = df.copy()
    df["color"] = df["title"].apply(extract_color)
    df["gender"] = df["title"].apply(extract_gender)
    df["size"] = df["title"].apply(extract_size)
    df["style"] = df["title"].apply(extract_style)
    df["category"] = df["title"].apply(extract_category)
    return df


def _build_combined_text(row: pd.Series) -> str:
    """Create a single searchable text blob for a product.

    It concatenates the original title, description (if present), all extracted
    attribute values and the overall sentiment.
    """
    parts = [row.get("title", ""), row.get("description", "")]
    for field in ["color", "gender", "size", "style", "category", "overall_sentiment"]:
        val = row.get(field)
        if val:
            parts.append(str(val))
    # Normalise whitespace and return the final string
    return " ".join(filter(None, parts))


def build_pipeline(
    meta_path: str,
    reviews_path: str,
    limit_reviews: Optional[int] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Execute the full ingestion pipeline.

    Returns a tuple ``(metadata_df, reviews_df)`` where ``metadata_df`` now
    contains the enriched columns and a ``combined_text`` field ready for
    embedding.
    """
    logger.info("Loading raw dataset …")
    meta_df, rev_df = load_dataset(meta_path, reviews_path)

    # ------------------------------------------------------------
    # 1️⃣ Review sentiment processing
    # ------------------------------------------------------------
    logger.info("Processing review sentiment …")
    rev_with_sentiment = process_reviews(rev_df, limit=limit_reviews)
    product_sentiment = aggregate_product_sentiment(rev_with_sentiment)

    # ------------------------------------------------------------
    # 2️⃣ Merge product‑level sentiment into metadata
    # ------------------------------------------------------------
    meta_df = meta_df.merge(product_sentiment, on="parent_asin", how="left")
    meta_df["overall_sentiment"] = meta_df["overall_sentiment"].fillna("neutral")

    # ------------------------------------------------------------
    # 3️⃣ Attribute extraction (rule‑based)
    # ------------------------------------------------------------
    logger.info("Extracting product attributes …")
    meta_df = _apply_attribute_extractors(meta_df)

    # ------------------------------------------------------------
    # 4️⃣ Build the searchable text blob
    # ------------------------------------------------------------
    logger.info("Building combined text for embedding …")
    meta_df["combined_text"] = meta_df.apply(_build_combined_text, axis=1)

    # ------------------------------------------------------------
    # 5️⃣ Upsert vectors into Pinecone
    # ------------------------------------------------------------
    logger.info("Generating embeddings and upserting to Pinecone …")
    upsert_vectors(meta_df, id_column="asin")

    logger.info("Pipeline completed successfully.")
    return meta_df, rev_with_sentiment


if __name__ == "__main__":
    # Simple CLI for manual runs – paths can be overridden via env vars or args.
    import os
    meta_path = os.getenv("META_PATH", "data/metadata.parquet")
    reviews_path = os.getenv("REVIEWS_PATH", "data/reviews.parquet")
    build_pipeline(meta_path, reviews_path)
