"""The query guard + translation, now part of QueryProcessor's single LLM call."""

import pytest

from app.retrieval.query_guard import NOT_FASHION_MESSAGE, has_fashion_term
from app.retrieval.query_processor import QueryProcessor
from tests.fakes import FakeLLM


@pytest.mark.parametrize("query", ["black jeans for men", "sneakers", "Dresses under 50", "what to wear to a wedding"])
def test_vocabulary_accepts_fashion_terms(query):
    assert has_fashion_term(query)


@pytest.mark.parametrize("query", ["pizza recipes", "weather today", "bitcoin price", "venues near me"])
def test_vocabulary_rejects_other_topics(query):
    assert not has_fashion_term(query)


def test_fallback_without_llm_uses_vocabulary():
    processor = QueryProcessor(FakeLLM(enabled=False))
    assert processor.process("red skirt").is_fashion
    refused = processor.process("pizza recipes")
    assert not refused.is_fashion and refused.message == NOT_FASHION_MESSAGE


def test_fallback_when_llm_fails():
    processor = QueryProcessor(FakeLLM(fail=True))
    assert processor.process("red skirt").search_query == "red skirt"
    assert not processor.process("pizza recipes").is_fashion


def test_llm_overrides_vocabulary_for_ambiguous_queries():
    # "wedding" is in the fashion vocabulary, but the LLM knows this isn't about clothes.
    result = QueryProcessor(FakeLLM({"is_fashion": False, "language": "en"})).process("wedding venues near me")
    assert not result.is_fashion and result.message == NOT_FASHION_MESSAGE


def test_llm_translates_and_regex_runs_on_the_english_text():
    llm = FakeLLM({"is_fashion": True, "language": "ES", "english_query": " blue jeans for men "})
    result = QueryProcessor(llm).process("jeans azules para hombre")
    assert result.is_fashion
    assert (result.search_query, result.translated_query, result.detected_language) == (
        "blue jeans for men", "blue jeans for men", "es",
    )
    assert (result.filters.color, result.filters.category, result.filters.gender) == ("blue", "jeans", "men")
    assert len(llm.calls) == 1


def test_english_query_reports_no_translation():
    llm = FakeLLM({"is_fashion": True, "language": "en", "english_query": "red skirt"})
    result = QueryProcessor(llm).process("red skirt")
    assert result.translated_query is None and result.detected_language == "en"


def test_answer_without_a_verdict_falls_back_to_vocabulary():
    processor = QueryProcessor(FakeLLM({"is_fashion": "yes"}))
    assert processor.process("red skirt").is_fashion
    assert not processor.process("pizza recipes").is_fashion


def test_llm_answers_are_cached():
    llm = FakeLLM({"is_fashion": True, "language": "en", "english_query": "red skirt"})
    processor = QueryProcessor(llm)
    processor.process("Red  skirt")
    processor.process("red skirt")
    assert len(llm.calls) == 1
