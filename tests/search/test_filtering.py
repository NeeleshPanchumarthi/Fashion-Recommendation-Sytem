from app.search.filtering import build_pinecone_filter, relax_once


def test_builds_pinecone_clauses():
    filters = {"gender": "men", "category": "shirt", "color": "black", "min_rating": 4.0, "sentiment": "positive"}
    assert build_pinecone_filter(filters) == {
        "gender": "men",
        "category": "shirt",
        "color": "black",
        "overall_sentiment": "positive",
        "average_rating": {"$gte": 4.0},
    }


def test_price_is_never_filtered():
    # Price isn't stored in Pinecone (most products have none).
    assert build_pinecone_filter({"category": "jeans", "price_min": 10.0, "price_max": 50.0}) == {"category": "jeans"}


def test_no_filters_returns_none():
    assert build_pinecone_filter({"gender": None, "category": None}) is None


def test_relax_drops_soft_filters_and_keeps_gender_category():
    filters = {"gender": "women", "category": "dress", "color": "red", "style": "party", "min_rating": 4.0}

    steps = []
    while (filters := relax_once(filters)) is not None:
        steps.append({k for k, v in filters.items() if v is not None})

    assert steps[-1] == {"gender", "category"}
    assert all({"gender", "category"} <= active for active in steps)
