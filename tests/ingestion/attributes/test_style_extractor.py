"""Tests for the style extraction module."""

import pytest
from app.ingestion.attributes.style_extractor import extract_style


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Men's Casual T-Shirt", "casual"),
        ("Formal Business Suit", "formal"),
        ("Athletic Running Shoes", "sporty"),
        ("Vintage Denim Jacket", "vintage"),
        ("Streetwear Oversized Hoodie", "streetwear"),
        ("Retro Graphic Tee", "retro"),
        ("Elegant Evening Gown", "elegant"),
        ("Basic Cotton Socks", None),
    ],
)
def test_extract_style(title: str, expected: str | None):
    assert extract_style(title) == expected
