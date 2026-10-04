import pytest
from app.domain.attributes.title_normalizer import normalize_title

@pytest.mark.parametrize(
    "input_title,expected_normalized",
    [
        ("  Red Shirt! ", "red shirt"),
        ("Men's Casual T‑Shirt", "men's casual t‑shirt"),
        ("&amp; Summer Dress!!", "& summer dress"),
        ("  Ultra‑Light   Jacket   ", "ultra‑light jacket"),
        ("***Special*Offer***", "special*offer"),
    ],
)
def test_normalize_title(input_title, expected_normalized):
    result = normalize_title(input_title)
    # original should be unchanged
    assert result["original"] == input_title
    # normalized should match expectation
    assert result["normalized"] == expected_normalized

def test_empty_string():
    result = normalize_title("")
    assert result["original"] == ""
    assert result["normalized"] == ""
