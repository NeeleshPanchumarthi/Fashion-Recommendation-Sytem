"""Product enrichment: turn a raw metadata batch plus its review analysis
into the product records that get embedded and indexed.

    merge review_highlights / overall_sentiment
      → title-based attribute extraction (color, gender, size, style, category)
      → explicit defaults for missing attributes
      → combined text (the embedding source)
"""

from __future__ import annotations

import pandas as pd

from app.domain.attributes.category_extractor import extract_category
from app.domain.attributes.color_extractor import extract_color
from app.domain.attributes.gender_extractor import extract_gender
from app.domain.attributes.size_extractor import extract_size
from app.domain.attributes.style_extractor import extract_style


def apply_attribute_extractors(
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


def build_combined_text(
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


def enrich(meta: pd.DataFrame, highlights_df: pd.DataFrame, sentiment_df: pd.DataFrame) -> pd.DataFrame:
    """Enriched product records with a 'combined_text' column."""
    meta = meta.merge(sentiment_df, on="parent_asin", how="left")
    meta = meta.merge(highlights_df, on="parent_asin", how="left")

    # Products with no reviews
    meta["overall_sentiment"] = meta["overall_sentiment"].fillna("neutral")
    meta["review_highlights"] = meta["review_highlights"].apply(lambda v: v if isinstance(v, list) else [])

    meta = apply_attribute_extractors(meta)
    meta["gender"] = meta["gender"].fillna("not specified")
    meta["color"] = meta["color"].fillna("not mentioned")
    meta["style"] = meta["style"].fillna("not specified")
    meta["category"] = meta["category"].fillna("not distributed")
    meta["description"] = meta.get(
        "description", pd.Series("no description", index=meta.index)
    ).fillna("no description")

    meta["combined_text"] = meta.apply(build_combined_text, axis=1)
    return meta
