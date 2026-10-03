"""End-to-end fashion ingestion pipeline.

TEST MODE is enabled by default:
1,000 metadata rows + 1,000 review rows.
"""

import logging
import os
from typing import Optional, Tuple

import pandas as pd

from .data_loader import load_dataset
from .review_processor import process_all_reviews
from .attributes.color_extractor import extract_color
from .attributes.gender_extractor import extract_gender
from .attributes.size_extractor import extract_size
from .attributes.style_extractor import extract_style
from .attributes.category_extractor import extract_category
from .vector_store import upsert_vectors


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _apply_attribute_extractors(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    title = df["title"].fillna("").astype(str)

    df["color"] = title.apply(extract_color)
    df["gender"] = title.apply(extract_gender)
    df["size"] = title.apply(extract_size)
    df["style"] = title.apply(extract_style)
    df["category"] = title.apply(extract_category)

    return df


def _build_combined_text(
    row: pd.Series,
) -> str:

    fields = [
        "title",
        "description",
        "color",
        "gender",
        "size",
        "style",
        "category",
        "overall_sentiment",
    ]

    parts = []

    for field in fields:

        value = row.get(field)

        if value is None:
            continue

        try:
            if hasattr(value, "size") and not isinstance(
                value, str
            ):
                if value.size == 0:
                    continue

            if not isinstance(value, (list, tuple)):
                if pd.isna(value):
                    continue

        except (TypeError, ValueError):
            pass

        if isinstance(value, (list, tuple)):

            if not value:
                continue

            value = " ".join(
                str(v) for v in value
            )

        elif hasattr(value, "flatten"):

            if value.size == 0:
                continue

            value = " ".join(
                str(v)
                for v in value.flatten()
            )

        else:
            value = str(value).strip()

        if value:
            parts.append(value)

    return " ".join(parts)


def build_pipeline(
    meta_path: str,
    reviews_path: str,
    sample_rows: Optional[int] = 1000,
    limit_reviews: Optional[int] = None,
    validate: bool = False,
    validate_relationship: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:

    logger.info("Starting fashion ingestion pipeline")

    if sample_rows is not None:
        logger.info(
            "TEST MODE: loading %d rows from each dataset",
            sample_rows,
        )
    else:
        logger.info("FULL DATASET MODE")

    # ---------------------------------------------------------
    # 1. Load datasets
    # ---------------------------------------------------------

    meta_df, rev_df = load_dataset(
        meta_path,
        reviews_path,
        sample_rows=sample_rows,
        validate=validate,
        validate_relationship=validate_relationship,
    )

    logger.info(
        "Loaded metadata: %d rows",
        len(meta_df),
    )

    logger.info(
        "Loaded reviews: %d rows",
        len(rev_df),
    )

    # ---------------------------------------------------------
    # 2. Review processing:
    #    score → bucket → top-K → local BERT sentiment
    #    → review_highlights (60/20/20) + overall_sentiment
    # ---------------------------------------------------------

    logger.info("Processing reviews (bucketed selection + local sentiment) …")

    rev_with_sentiment, highlights_df, sentiment_df = process_all_reviews(
        rev_df,
        limit=limit_reviews,
    )

    # ---------------------------------------------------------
    # 3. Merge review_highlights and overall_sentiment
    # ---------------------------------------------------------

    meta_df = meta_df.merge(
        sentiment_df,   # columns: parent_asin, overall_sentiment
        on="parent_asin",
        how="left",
    )

    meta_df = meta_df.merge(
        highlights_df,  # columns: parent_asin, review_highlights
        on="parent_asin",
        how="left",
    )

    # Fill products with no reviews
    meta_df["overall_sentiment"] = (
        meta_df["overall_sentiment"].fillna("neutral")
    )
    meta_df["review_highlights"] = meta_df["review_highlights"].apply(
        lambda v: v if isinstance(v, list) else []
    )

    # ---------------------------------------------------------
    # 4. Attributes
    # ---------------------------------------------------------

    logger.info("Extracting product attributes...")

    meta_df = _apply_attribute_extractors(meta_df)

    # Fill optional attribute fields with explicit "not specified" / defaults
    meta_df["gender"] = meta_df["gender"].fillna("not specified")
    meta_df["color"] = meta_df["color"].fillna("not mentioned")
    meta_df["style"] = meta_df["style"].fillna("not specified")
    meta_df["category"] = meta_df["category"].fillna("not distributed")
    meta_df["description"] = meta_df.get(
        "description", pd.Series("no description", index=meta_df.index)
    ).fillna("no description")

    # ---------------------------------------------------------
    # 5. Combined text
    # ---------------------------------------------------------

    logger.info("Building combined text...")

    meta_df["combined_text"] = meta_df.apply(
        _build_combined_text,
        axis=1,
    )

    # ---------------------------------------------------------
    # 6. Pinecone – upsert with full metadata
    # ---------------------------------------------------------

    logger.info(
        "Generating embeddings and upserting to Pinecone..."
    )

    upsert_vectors(
        meta_df,
        id_column="parent_asin",
    )

    logger.info(
        "Pipeline completed successfully."
    )

    return meta_df, rev_with_sentiment


if __name__ == "__main__":

    meta_path = os.getenv(
        "META_PATH",
        "data/metadata.parquet",
    )

    reviews_path = os.getenv(
        "REVIEWS_PATH",
        "data/reviews.parquet",
    )

    sample_rows_env = os.getenv(
        "SAMPLE_ROWS",
        "1000",
    )

    if sample_rows_env.lower() == "all":
        sample_rows = None
    else:
        sample_rows = int(sample_rows_env)

    validate = (
        os.getenv(
            "VALIDATE_DATASET",
            "false",
        ).lower()
        == "true"
    )

    validate_relationship = (
        os.getenv(
            "VALIDATE_RELATIONSHIP",
            "false",
        ).lower()
        == "true"
    )

    build_pipeline(
        meta_path=meta_path,
        reviews_path=reviews_path,
        sample_rows=sample_rows,
        validate=validate,
        validate_relationship=validate_relationship,
    )