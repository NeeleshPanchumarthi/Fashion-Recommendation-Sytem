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
