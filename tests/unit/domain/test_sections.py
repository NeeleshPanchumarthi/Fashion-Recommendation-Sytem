import pytest

from app.domain.sections import effective_gender, is_accessory


@pytest.mark.parametrize(
    "gender, category, title, expected",
    [
        ("men", "shirt", "Red Shirt", "men"),
        ("not specified", None, "Women's Floral Top", "women"),  # title fallback
        (None, "dress", "Floral Maxi Dress", "women"),            # women-only garment
        (None, "jeans", "Slim Fit Jeans", None),
        ("unisex", "hoodie", "Hoodie", "unisex"),
    ],
)
def test_effective_gender(gender, category, title, expected):
    assert effective_gender(gender, category, title) == expected


@pytest.mark.parametrize(
    "category, title, expected",
    [
        ("cap", "Baseball Cap", True),
        (None, "Leather Belt for Men", True),
        (None, "Polarized Sunglasses", True),
        ("shirt", "Men's Red Shirt", False),
        ("shoes", "Leather Belt Buckle Shoes", False),  # footwear is not an accessory
        (None, "Ring Spun Cotton Tie Dye Tee", False),
    ],
)
def test_is_accessory(category, title, expected):
    assert is_accessory(category, title) is expected
