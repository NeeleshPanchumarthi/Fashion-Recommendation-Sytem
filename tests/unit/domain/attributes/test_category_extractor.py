"""Tests for the category extraction module."""

import pytest
from app.domain.attributes.category_extractor import extract_category


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Men's Graphic T-Shirt", "t-shirt"),
        ("Classic Summer Dress", "dress"),
        ("Slim Fit Blue Jeans", "jeans"),
        ("Winter Heavy Coat", "coat"),
        ("Running Sneakers for Women", "sneakers"),
        ("Leather Boots", "shoes"),
        ("Cotton Casual Shirt", "shirt"),
        ("Warm Fleece Hoodie", "hoodie"),
        ("Unisex Baseball Cap", "hat"),
        ("Unknown Vintage Item", None),
    ],
)
def test_extract_category(title: str, expected: str | None):
    assert extract_category(title) == expected
