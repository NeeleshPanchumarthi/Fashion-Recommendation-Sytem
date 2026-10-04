from app.domain.search import SearchFilters


def test_relaxed_drops_soft_filters_in_order_and_never_gender_or_category():
    filters = SearchFilters(gender="women", category="dress", color="red", style="party", min_rating=4.0)

    steps = []
    while (filters := filters.relaxed()) is not None:
        steps.append(set(filters.applied()))

    assert steps == [
        {"gender", "category", "color", "style"},  # min_rating first
        {"gender", "category", "color"},
        {"gender", "category"},
    ]


def test_applied_hides_internal_gender_exclusions():
    assert SearchFilters(category="shirt", exclude_genders=("men",)).applied() == {"category": "shirt"}
