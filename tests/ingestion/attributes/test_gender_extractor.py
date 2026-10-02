"""Tests for the gender extraction module.

These tests validate that :func:`extract_gender` correctly maps various
product title strings to the canonical gender categories defined in
``app.ingestion.attributes.vocabularies.GENDERS``.  The test suite is fully
parameterised to keep it concise while covering typical edge‑cases such as
punctuation, mixed‑case, and titles that contain no gender information.
"""

import pytest
from app.ingestion.attributes.gender_extractor import extract_gender

@pytest.mark.parametrize(
    "title,expected",
    [
        ("Men's Casual Shirt", "men"),
        ("Women's Summer Dress", "women"),
        ("Kids' Playground Set", "kids"),
        ("Unisex Baseball Cap", "unisex"),
        ("Adult T‑Shirt", None),
        ("MEN Trousers", "men"),
        ("women shoes", "women"),
        ("Kids-Playwear", "kids"),
        ("Super‑Unisex Hoodie", "unisex"),
        ("Classic Jacket", None),
    ],
)
def test_extract_gender(title: str, expected: str | None):
    assert extract_gender(title) == expected
