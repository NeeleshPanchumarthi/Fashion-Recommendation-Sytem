"""Tests for the color extraction module."""

import pytest
from app.domain.attributes.color_extractor import extract_color


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Men's Red T-Shirt", "red"),
        ("Women's Navy Blue Dress", "navy"),
        ("Slim Fit Gray Jeans", "grey"),
        ("Black Leather Jacket", "black"),
        ("Pure White Sneakers", "white"),
        ("Classic Brown Boots", "brown"),
        ("Golden Party Watch", "gold"),
        ("Silver Pendant Necklace", "silver"),
        ("Plain Cotton Hoodie", None),
    ],
)
def test_extract_color(title: str, expected: str | None):
    assert extract_color(title) == expected
