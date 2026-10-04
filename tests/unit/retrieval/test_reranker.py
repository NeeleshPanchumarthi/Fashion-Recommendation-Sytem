from app.domain.product import Product, ProductMatch
from app.retrieval.reranker import Reranker, candidate_text
from tests.fakes import FakeRerankerClient


def _match(pid, title, **fields):
    return ProductMatch(product=Product(product_id=pid, title=title, **fields), score=0.0)


def test_candidate_text_joins_present_fields_in_order():
    product = Product(product_id="A", title="Red Shirt", category="shirt", color=None, gender="men")
    assert candidate_text(product) == "Red Shirt shirt men"


def test_rerank_sorts_by_score_and_sets_rerank_score():
    ranked = Reranker(FakeRerankerClient()).rerank(
        "red party shirt",
        [_match("a", "Blue jeans"), _match("b", "Red party shirt"), _match("c", "Red shirt")],
    )
    assert [m.product.product_id for m in ranked] == ["b", "c", "a"]
    assert ranked[0].rerank_score == 3.0


def test_candidates_without_text_go_last():
    ranked = Reranker(FakeRerankerClient()).rerank("shirt", [_match("empty", ""), _match("s", "Shirt")])
    assert [m.product.product_id for m in ranked] == ["s", "empty"]
    assert ranked[1].rerank_score == float("-inf")
