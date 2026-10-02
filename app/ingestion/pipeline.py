"""End-to-end fashion ingestion pipeline.

TEST MODE is enabled by default:
1,000 metadata rows + 1,000 review rows.
"""

import logging
import os
from typing import Optional, Tuple

import pandas as pd

from .data_loader import load_dataset
from .review_processor import (
    process_reviews,
    aggregate_product_sentiment,
)
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
    # 2. Sentiment
    # ---------------------------------------------------------

    logger.info("Processing review sentiment...")

    rev_with_sentiment = process_reviews(
        rev_df,
        limit=limit_reviews,
    )

    product_sentiment = aggregate_product_sentiment(
        rev_with_sentiment
    )

    # ---------------------------------------------------------
    # 3. Merge sentiment
    # ---------------------------------------------------------

    meta_df = meta_df.merge(
        product_sentiment,
        on="parent_asin",
        how="left",
    )

    meta_df["overall_sentiment"] = (
        meta_df["overall_sentiment"]
        .fillna("neutral")
    )

    # ---------------------------------------------------------
    # 4. Attributes
    # ---------------------------------------------------------

    logger.info("Extracting product attributes...")

    meta_df = _apply_attribute_extractors(meta_df)

    # ---------------------------------------------------------
    # 5. Combined text
    # ---------------------------------------------------------

    logger.info("Building combined text...")

    meta_df["combined_text"] = meta_df.apply(
        _build_combined_text,
        axis=1,
    )

    # ---------------------------------------------------------
    # 6. Pinecone
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
        "100",
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