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


def test_dress_category_dropped_for_men_only():
    others, men = gender_pools(SearchFilters(category="dress"))
    assert others.category == "dress"
    assert men.category is None


def test_women_only_garments_stay_filtered_for_men():
    _, men = gender_pools(SearchFilters(category="skirt"))
    assert men.category == "skirt"


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
