"""Review processing – bucketed selection + local sentiment analysis.

Pipeline
--------
Reviews
  → score_reviews()           – compute a quality score per review
  → select_reviews()          – bucket by rating (1-2★/3★/4-5★), pick top-K per bucket
  → run_sentiment_pipeline()  – classify with local BERT model
  → build_review_highlights() – 60 % positive / 20 % neutral / 20 % negative
  → aggregate_product_sentiment() – majority label per product
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Aspect-keyword pattern (fashion-relevant terms)
# ---------------------------------------------------------------------------

ASPECTS = (
    r"\b(fit|fits|size|sizing|small|large|tight|loose|fabric|material|soft|"
    r"stretch|thin|thick|breathable|comfortable|wore|wear|worn|wedding|party|"
    r"beach|gym|work|office|summer|winter|warm|cool|quality|wash|shrunk|"
    r"color|colour)\b"
)

# Fixed reference date so chunked runs produce identical scores
REF_DATE = pd.Timestamp("2023-09-01")


# ---------------------------------------------------------------------------
# Top-K thresholds per product
# ---------------------------------------------------------------------------

def _k_for_count(n: int) -> int:
    """Return how many reviews to keep per rating bucket.

    Total reviews per product  →  keep per bucket
    1–3                        →  all  (process all reviews)
    4–10                       →  up to 2  (≤6 total across 3 buckets)
    10+                        →  up to 3  (≤9 total across 3 buckets)
    """
    if n <= 3:
        return n      # process all
    elif n <= 10:
        return 2      # up to 6 total (2 × 3 buckets)
    else:
        return 3      # up to 9 total (3 × 3 buckets)


# ---------------------------------------------------------------------------
# Step 1: Quality score
# ---------------------------------------------------------------------------

def score_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    """Calculate a review-quality / informativeness score.

    The score measures how *useful* a review is – it does NOT determine
    sentiment.

    Scoring components
    ------------------
    +1.0 × log(1 + helpful_votes)    – community-validated helpfulness
    +0.5 × verified_purchase         – verified buyers are more trustworthy
    +0.8 × min(aspect_hits, 4) / 4  – fashion-relevant content (capped at 4)
    +0.5 × clip(len, 0, 400) / 400  – length bonus (up to 400 chars)
    −0.5 × (len > 1500)             – penalty for very long / rambling reviews
    +0.3 / (1 + age_years)          – recency bonus
    """
    r = reviews.copy()

    # Normalise timestamp column name (supports both "ts" and "timestamp")
    ts_col = "ts" if "ts" in r.columns else "timestamp"
    if ts_col not in r.columns:
        r["ts"] = REF_DATE
    else:
        r["ts"] = pd.to_datetime(r[ts_col], unit="ms", errors="coerce").fillna(REF_DATE)

    # 1. Length
    r["len"] = r["text"].fillna("").astype(str).str.len()

    # 2. Fashion-relevant aspect mentions
    r["aspect_hits"] = (
        r["text"].fillna("").astype(str).str.count(ASPECTS, flags=re.I)
    )

    # 3. Review age in years
    age_years = (REF_DATE - r["ts"]).dt.days.clip(lower=0) / 365

    # Helper: safely get optional columns
    helpful_votes = r["helpful_vote"].fillna(0) if "helpful_vote" in r.columns else pd.Series(0, index=r.index)
    verified = r["verified_purchase"].fillna(False).astype(float) if "verified_purchase" in r.columns else pd.Series(0.0, index=r.index)

    # 4. Composite quality score
    r["score"] = (
          1.0 * np.log1p(helpful_votes)
        + 0.5 * verified
        + 0.8 * np.minimum(r["aspect_hits"], 4) / 4
        + 0.5 * np.clip(r["len"], 0, 400) / 400
        - 0.5 * (r["len"] > 1500).astype(float)
        + 0.3 / (1 + age_years)
    )

    return r


# ---------------------------------------------------------------------------
# Step 2: Bucket + dynamic top-K selection
# ---------------------------------------------------------------------------

def select_reviews(scored_reviews: pd.DataFrame) -> pd.DataFrame:
    """Bucket reviews by star rating and select the top-K per bucket.

    Buckets
    -------
    low    : 1–2 ★
    middle : 3 ★
    high   : 4–5 ★

    Top-K per bucket is derived from the *total* number of reviews for
    that product so that small catalogues are not penalised.

    Implementation note
    -------------------
    We deliberately avoid groupby().apply() here because pandas 2.x can
    silently drop the groupby-key columns (e.g. parent_asin) from the
    result.  Instead we use transform('rank') so that all columns are
    preserved through a simple boolean filter.
    """
    r = scored_reviews.copy().reset_index(drop=True)

    # Rating buckets
    r["rating_bucket"] = pd.cut(
        r["rating"],
        bins=[0, 2.5, 3.5, 5.0],
        labels=["low", "middle", "high"],
        include_lowest=True,
    )

    # Per-product total review count → dynamic K
    product_counts = r.groupby("parent_asin")["rating"].transform("count")
    r["_k"] = product_counts.map(_k_for_count)

    # Rank each review within its (product, bucket) group by quality score.
    # rank(ascending=False) gives 1 to the best-scoring review.
    r["_rank"] = (
        r.groupby(["parent_asin", "rating_bucket"], observed=True)["score"]
        .rank(method="first", ascending=False)
    )

    # Keep only reviews whose rank is within the per-product K
    selected = r[r["_rank"] <= r["_k"]].drop(columns=["_k", "_rank"]).reset_index(drop=True)

    return selected


# ---------------------------------------------------------------------------
# Step 3: Local sentiment model (nlptown BERT)
# ---------------------------------------------------------------------------

def run_sentiment_pipeline(selected_reviews: pd.DataFrame) -> pd.DataFrame:
    """Run nlptown/bert-base-multilingual-uncased-sentiment on selected reviews.

    Star predictions are mapped to three labels:
        1–2 stars → negative
        3 stars   → neutral
        4–5 stars → positive

    The transformers pipeline is loaded lazily and cached inside
    sentiment_extractor so that repeated calls don't reload the model.
    """
    from app.ingestion.sentiment_extractor import classify_batch  # lazy import

    df = selected_reviews.copy()
    texts = df["text"].fillna("").astype(str).tolist()

    logger.info("Running local sentiment model on %d selected reviews …", len(texts))
    labels = classify_batch(texts)

    df["sentiment"] = labels
    return df


# ---------------------------------------------------------------------------
# Step 4: Build review_highlights per product (60/20/20 mix)
# ---------------------------------------------------------------------------

def build_review_highlights(
    df_with_sentiment: pd.DataFrame,
    pos_frac: float = 0.60,
    neu_frac: float = 0.20,
    neg_frac: float = 0.20,
) -> pd.DataFrame:
    """Construct review_highlights per product.

    The highlights target a 60 / 20 / 20 positive / neutral / negative mix.
    When a sentiment bucket has fewer reviews than the target share we take
    all available reviews; shortfalls are back-filled from the positive bucket.

    Returns
    -------
    DataFrame with columns: parent_asin, review_highlights
    where review_highlights is a list[str] of selected review texts.
    """
    results = []

    for asin, group in df_with_sentiment.groupby("parent_asin"):
        pos = group[group["sentiment"] == "positive"]["text"].tolist()
        neu = group[group["sentiment"] == "neutral"]["text"].tolist()
        neg = group[group["sentiment"] == "negative"]["text"].tolist()

        total = len(group)
        if total == 0:
            results.append({"parent_asin": asin, "review_highlights": []})
            continue

        n_pos = max(1, round(total * pos_frac))
        n_neu = max(0, round(total * neu_frac))
        n_neg = max(0, round(total * neg_frac))

        chosen_pos = pos[:n_pos]
        chosen_neu = neu[:n_neu]
        chosen_neg = neg[:n_neg]

        # Fill any shortfall with extra positive reviews
        shortfall = (
            (n_pos - len(chosen_pos))
            + (n_neu - len(chosen_neu))
            + (n_neg - len(chosen_neg))
        )
        extra_pos = pos[n_pos: n_pos + shortfall]

        highlights = chosen_pos + extra_pos + chosen_neu + chosen_neg

        results.append({
            "parent_asin": asin,
            "review_highlights": highlights,
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Step 5: Overall product sentiment (majority vote)
# ---------------------------------------------------------------------------

def aggregate_product_sentiment(df_with_sentiment: pd.DataFrame) -> pd.DataFrame:
    """Derive a single overall_sentiment label per product via majority vote.

    Returns
    -------
    DataFrame with columns: parent_asin, overall_sentiment
    """
    if "sentiment" not in df_with_sentiment.columns:
        raise ValueError("DataFrame must contain a 'sentiment' column.")

    agg = (
        df_with_sentiment.groupby("parent_asin")["sentiment"]
        .agg(lambda x: x.mode().iloc[0] if not x.mode().empty else "neutral")
        .reset_index()
        .rename(columns={"sentiment": "overall_sentiment"})
    )
    return agg


# ---------------------------------------------------------------------------
# Convenience: full review processing entry point
# ---------------------------------------------------------------------------

def process_all_reviews(
    df_reviews: pd.DataFrame,
    limit: Optional[int] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the complete review processing pipeline.

    Parameters
    ----------
    df_reviews : raw reviews DataFrame
    limit      : optional row limit for quick testing

    Returns
    -------
    selected_with_sentiment : per-review DataFrame with a 'sentiment' column
    highlights_df           : per-product DataFrame with 'review_highlights'
    sentiment_df            : per-product DataFrame with 'overall_sentiment'
    """
    if limit is not None:
        df_reviews = df_reviews.head(limit).copy()

    logger.info("Step 1/4 – Scoring %d reviews …", len(df_reviews))
    scored = score_reviews(df_reviews)

    logger.info("Step 2/4 – Selecting top-K per rating bucket …")
    selected = select_reviews(scored)
    logger.info("Selected %d reviews from %d total", len(selected), len(scored))

    logger.info("Step 3/4 – Running local sentiment model …")
    with_sentiment = run_sentiment_pipeline(selected)

    logger.info("Step 4/4 – Building highlights & aggregating sentiment …")
    highlights_df = build_review_highlights(with_sentiment)
    sentiment_df = aggregate_product_sentiment(with_sentiment)

    return with_sentiment, highlights_df, sentiment_df
