import pandas as pd

from app.services.product_enrichment_service import enrich


def test_enrich_merges_reviews_extracts_attributes_and_builds_text():
    meta = pd.DataFrame({
        "parent_asin": ["A1", "A2"],
        "title": ["Men's Red Party Shirt Large", "Plain thing"],
        "description": ["Cotton shirt", None],
    })
    highlights = pd.DataFrame({"parent_asin": ["A1"], "review_highlights": [["Great fit"]]})
    sentiment = pd.DataFrame({"parent_asin": ["A1"], "overall_sentiment": ["positive"]})

    out = enrich(meta, highlights, sentiment).set_index("parent_asin")

    shirt, plain = out.loc["A1"], out.loc["A2"]
    assert (shirt["gender"], shirt["color"], shirt["category"]) == ("men", "red", "shirt")
    assert shirt["review_highlights"] == ["Great fit"]
    assert shirt["combined_text"].startswith("Men's Red Party Shirt Large Cotton shirt red men")

    # Products without reviews or attributes get explicit defaults.
    assert plain["overall_sentiment"] == "neutral"
    assert plain["review_highlights"] == []
    assert (plain["gender"], plain["color"], plain["category"]) == ("not specified", "not mentioned", "not distributed")
    assert plain["description"] == "no description"
