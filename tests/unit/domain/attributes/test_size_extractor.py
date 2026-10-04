"""Tests for the size extraction module."""

import pytest
from app.domain.attributes.size_extractor import extract_size


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Men's T-Shirt Size M", "m"),
        ("Casual Dress - Size XL", "xl"),
        ("Women's Small Top", "s"),
        ("Large Leather Jacket", "l"),
        ("Extra-Large Hoodie", "xl"),
        ("Size 2XL Sweatshirt", "xxl"),
        ("Classic Blue Jeans", None),
    ],
)
def test_extract_size(title: str, expected: str | None):
    assert extract_size(title) == expected
