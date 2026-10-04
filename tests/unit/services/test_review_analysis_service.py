import pandas as pd

from app.services.review_analysis_service import (
    ReviewAnalysisService,
    aggregate_product_sentiment,
    build_review_highlights,
    score_reviews,
    select_reviews,
)
from tests.fakes import FakeSentimentClient


def _reviews(rows):
    df = pd.DataFrame(rows, columns=["parent_asin", "rating", "text"])
    df["timestamp"] = 1_690_000_000_000
    df["verified_purchase"] = True
    df["helpful_vote"] = 0
    return df


def test_score_rewards_fashion_aspects_and_length():
    scored = score_reviews(_reviews([("A", 5, "ok"), ("A", 5, "Great fit and soft fabric, true to size")]))
    assert scored["score"].iloc[1] > scored["score"].iloc[0]


def test_select_keeps_top_k_per_rating_bucket():
    # 12 reviews -> keep up to 3 per bucket; all are 5-star here.
    rows = [("A", 5, "great fit " * i) for i in range(1, 13)]
    selected = select_reviews(score_reviews(_reviews(rows)))
    assert len(selected) == 3


def test_small_products_keep_every_review():
    selected = select_reviews(score_reviews(_reviews([("A", 1, "bad"), ("A", 3, "meh"), ("A", 5, "great")])))
    assert len(selected) == 3


def test_highlights_and_majority_sentiment():
    df = pd.DataFrame({
        "parent_asin": ["A"] * 5,
        "text": ["p1", "p2", "p3", "n1", "neg1"],
        "sentiment": ["positive", "positive", "positive", "neutral", "negative"],
    })
    highlights = build_review_highlights(df).set_index("parent_asin")["review_highlights"]["A"]
    assert highlights == ["p1", "p2", "p3", "n1", "neg1"]
    assert aggregate_product_sentiment(df)["overall_sentiment"].tolist() == ["positive"]


def test_analyze_end_to_end_with_fake_model():
    service = ReviewAnalysisService(FakeSentimentClient())
    highlights, sentiment = service.analyze(_reviews([("A", 5, "Love it"), ("A", 5, "Great"), ("B", 1, "bad")]))
    assert dict(zip(sentiment["parent_asin"], sentiment["overall_sentiment"])) == {"A": "positive", "B": "negative"}
    assert set(highlights["parent_asin"]) == {"A", "B"}


def test_analyze_without_reviews_returns_empty_frames():
    highlights, sentiment = ReviewAnalysisService(FakeSentimentClient()).analyze(_reviews([]))
    assert highlights.empty and list(highlights.columns) == ["parent_asin", "review_highlights"]
    assert sentiment.empty and list(sentiment.columns) == ["parent_asin", "overall_sentiment"]
