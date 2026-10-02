"""Tests for the aggregated attribute extractor."""

from app.ingestion.attributes.attribute_extractor import extract_all_attributes


def test_extract_all_attributes_full():
    title = "Men's Red Casual T-Shirt Size XL"
    attributes = extract_all_attributes(title)
    assert attributes["gender"] == "men"
    assert attributes["color"] == "red"
    assert attributes["style"] == "casual"
    assert attributes["category"] == "t-shirt"
    assert attributes["size"] == "xl"


def test_extract_all_attributes_partial():
    title = "Vintage Black Dress"
    attributes = extract_all_attributes(title)
    assert attributes["gender"] is None
    assert attributes["color"] == "black"
    assert attributes["style"] == "vintage"
    assert attributes["category"] == "dress"
    assert attributes["size"] is None
