import pytest

from app.domain.tryon import garment_type_for


@pytest.mark.parametrize(
    "category, expected",
    [
        ("t-shirt", "upper_body"),
        ("hoodie", "upper_body"),
        ("jacket", "upper_body"),
        ("jeans", "lower_body"),
        ("skirt", "lower_body"),
        ("dress", "dresses"),
        ("shoes", None),
        ("hat", None),
    ],
)
def test_garment_type_from_category(category, expected):
    assert garment_type_for(category) == expected


def test_falls_back_to_title_when_category_missing():
    assert garment_type_for(None, "Women's Summer Floral Midi Dress") == "dresses"
    assert garment_type_for(None, "Leather Ankle Boots") is None
    assert garment_type_for(None, None) is None
