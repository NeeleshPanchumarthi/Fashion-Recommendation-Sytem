from app.domain.product import Product, ProductMatch
from app.domain.search import SearchFilters
from app.repositories.vector_repository import VectorRepository
from app.retrieval.retriever import Retriever, gender_pools, interleave
from tests.fakes import FakePineconeClient, product_vector


def _hit(pid, score):
    return ProductMatch(product=Product(product_id=pid, title=pid), score=0.0, rerank_score=score)


def test_resolved_gender_searches_one_pool_unchanged():
    filters = SearchFilters(gender="women", category="dress")
    assert gender_pools(filters) == [filters]


def test_no_gender_searches_others_without_kids_and_men():
    others, men = gender_pools(SearchFilters(category="shirt", color="black"))
    assert others == SearchFilters(category="shirt", color="black", exclude_genders=("men", "kids"))
    assert men == SearchFilters(gender="men", category="shirt", color="black")


def test_women_only_garments_skip_the_mens_pool():
    for category in ("dress", "skirt", "blouse"):
        assert gender_pools(SearchFilters(category=category)) == [
            SearchFilters(category=category, exclude_genders=("men", "kids"))
        ]


def test_interleave_alternates_starting_with_best_pool():
    women = [_hit("w1", 0.5), _hit("w2", 0.1), _hit("w3", -1.0)]
    men = [_hit("m1", 0.9), _hit("m2", -0.5)]
    assert [m.product.product_id for m in interleave([women, men])] == ["m1", "w1", "m2", "w2", "w3"]


def test_interleave_skips_empty_pool_and_dedupes():
    assert [m.product.product_id for m in interleave([[_hit("a", 1), _hit("b", 0)], []])] == ["a", "b"]
    assert [m.product.product_id for m in interleave([[_hit("a", 1)], [_hit("a", 0.5), _hit("c", 0)]])] == ["a", "c"]


def test_relaxes_soft_filters_until_enough_results_but_keeps_category():
    vectors = [product_vector(f"S{i}", f"Shirt {i}", category="shirt", color="blue") for i in range(6)]
    client = FakePineconeClient(vectors)
    retriever = Retriever(VectorRepository(client), dense_k=50)

    matches, used = retriever.retrieve([0.0], SearchFilters(category="shirt", color="red", style="party"))

    assert len(matches) == 6
    assert used == SearchFilters(category="shirt")  # style dropped, then color
    assert client.queries[-1] == {"category": "shirt"}


def test_stops_relaxing_when_only_hard_filters_remain():
    client = FakePineconeClient([])
    matches, used = Retriever(VectorRepository(client), dense_k=50).retrieve([0.0], SearchFilters(gender="men", color="red"))
    assert matches == []
    assert used == SearchFilters(gender="men")


def test_outfit_plan_covers_every_group_per_gender_pool():
    from app.retrieval.retriever import plan_subqueries

    plan = plan_subqueries(SearchFilters(color="red", style="party"), outfit=True)
    assert [(sq.group, sq.filters.gender) for sq in plan] == [
        ("tops", None), ("bottoms", None), ("footwear", None), ("accessories", None),
        ("tops", "men"), ("bottoms", "men"), ("footwear", "men"), ("accessories", "men"),
    ]
    assert all(sq.filters.color == "red" and sq.filters.style is None for sq in plan)
    assert all(sq.filters.categories for sq in plan if sq.group != "accessories")


def test_relax_all_at_once_costs_at_most_two_searches():
    client = FakePineconeClient([product_vector("S1", "Shirt", category="shirt")])
    retriever = Retriever(VectorRepository(client), dense_k=10)
    _, used = retriever.retrieve([0.0], SearchFilters(category="shirt", color="red", style="party", size="m"),
                                 relax_all_at_once=True)
    assert len(client.queries) == 2
    assert used == SearchFilters(category="shirt")
