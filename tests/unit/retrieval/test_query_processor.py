from app.domain.search import SearchFilters
from app.retrieval.query_processor import QueryProcessor, extract_query_gender
from tests.fakes import FakeLLM


def test_query_gender_cues():
    assert extract_query_gender("I need a dress for wedding") is None
    assert extract_query_gender("men's shirt for party") == "men"
    assert extract_query_gender("a dress for my wife") == "women"
    assert extract_query_gender("gift for my husband") == "men"
    assert extract_query_gender("matching outfits for him and her") is None
    assert extract_query_gender("girls party dress") is None
    # Word boundaries: "her" inside "weather"/"leather" is not a cue.
    assert extract_query_gender("leather jacket for cold weather") is None


def test_regex_wins_and_llm_fills_gaps():
    llm = FakeLLM({"category": "jeans", "color": "green", "style": "casual", "expanded_query": "casual blue jeans"})
    result = QueryProcessor(llm).process("blue jeans under 50")

    assert result.filters == SearchFilters(category="jeans", color="blue", style="casual")
    assert result.sources == {"category": "regex", "color": "regex", "style": "llm", "price_max": "regex"}
    assert result.expanded_query == "casual blue jeans"
    assert result.price_max == 50.0  # extracted, but never a filter


def test_llm_values_outside_vocabulary_are_discarded():
    result = QueryProcessor(FakeLLM({"color": "chartreuse-ish", "gender": "WOMEN"})).process("something nice")
    assert result.filters == SearchFilters(gender="women")


def test_llm_failure_falls_back_to_regex_and_original_query():
    result = QueryProcessor(FakeLLM(fail=True)).process("red skirt")
    assert result.filters == SearchFilters(category="skirt", color="red")
    assert result.expanded_query == "red skirt"


def test_disabled_llm_is_not_called():
    llm = FakeLLM(enabled=False)
    QueryProcessor(llm).process("red skirt")
    assert llm.calls == []


def test_general_clothing_words_make_an_outfit_query():
    for query in ["outfit for a party", "wedding attire", "something to wear to college", "party wear"]:
        result = QueryProcessor(FakeLLM(enabled=False)).process(query)
        assert result.outfit, query
        assert result.filters.category is None, query


def test_named_garments_are_not_outfit_queries():
    # "dress" is a garment (a one-piece), not a general word for clothes.
    for query in ["black jeans for men", "party shirt", "red skirt", "outfit with jeans", "I need a dress for wedding"]:
        assert not QueryProcessor(FakeLLM(enabled=False)).process(query).outfit, query


def test_relation_phrases_become_a_filter_not_search_text():
    from app.retrieval.query_processor import strip_relation_phrases

    assert strip_relation_phrases("outfit for my husband for a party") == "outfit for a party"
    assert strip_relation_phrases("dress for my wife") == "dress"
    assert strip_relation_phrases("mother of the bride dress") == "mother of the bride dress"
    assert strip_relation_phrases("for my wife") == "for my wife"  # nothing left -> keep original

    result = QueryProcessor(FakeLLM(enabled=False)).process("outfit for my husband for a party")
    assert result.filters.gender == "men"
    assert result.search_query == result.expanded_query == "outfit for a party"


def test_dress_as_a_modifier_keeps_the_real_garment():
    for query, category in [("dress shirt", "shirt"), ("dress pants for office", "pants"), ("black dress shoes", "shoes")]:
        result = QueryProcessor(FakeLLM(enabled=False)).process(query)
        assert not result.outfit, query
        assert result.filters.category == category, query
