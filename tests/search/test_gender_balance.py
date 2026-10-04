from app.search.gender_balance import gender_pools, interleave
from app.search.query_understanding import extract_query_gender


def _hit(id_, score):
    return {"id": id_, "rerank_score": score, "metadata": {}}


def test_resolved_gender_searches_one_pool_unchanged():
    filters = {"gender": "women", "category": "dress"}
    assert gender_pools(filters) == [filters]


def test_no_gender_searches_men_and_others_without_kids():
    others, men = gender_pools({"gender": None, "category": "shirt", "color": "black"})
    assert others == {"gender": {"$nin": ["men", "kids"]}, "category": "shirt", "color": "black"}
    assert men == {"gender": "men", "category": "shirt", "color": "black"}


def test_dress_category_dropped_for_men_only():
    others, men = gender_pools({"gender": None, "category": "dress"})
    assert others["category"] == "dress"
    assert men["category"] is None


def test_women_only_garments_stay_filtered_for_men():
    _, men = gender_pools({"gender": None, "category": "skirt"})
    assert men["category"] == "skirt"


def test_interleave_alternates_starting_with_best_pool():
    women = [_hit("w1", 0.5), _hit("w2", 0.1), _hit("w3", -1.0)]
    men = [_hit("m1", 0.9), _hit("m2", -0.5)]
    assert [h["id"] for h in interleave([women, men])] == ["m1", "w1", "m2", "w2", "w3"]


def test_interleave_skips_empty_pool_and_dedupes():
    assert [h["id"] for h in interleave([[_hit("a", 1), _hit("b", 0)], []])] == ["a", "b"]
    assert [h["id"] for h in interleave([[_hit("a", 1)], [_hit("a", 0.5), _hit("c", 0)]])] == ["a", "c"]


def test_query_gender_cues():
    assert extract_query_gender("I need a dress for wedding") is None
    assert extract_query_gender("men's shirt for party") == "men"
    assert extract_query_gender("a dress for my wife") == "women"
    assert extract_query_gender("gift for my husband") == "men"
    assert extract_query_gender("matching outfits for him and her") is None
    assert extract_query_gender("girls party dress") is None
    # Word boundaries: "her" inside "weather"/"leather" is not a cue.
    assert extract_query_gender("leather jacket for cold weather") is None
