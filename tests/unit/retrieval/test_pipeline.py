from app.repositories.vector_repository import VectorRepository
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.query_processor import QueryProcessor
from app.retrieval.reranker import Reranker
from app.retrieval.retriever import Retriever
from tests.fakes import FakeEmbedder, FakeLLM, FakePineconeClient, FakeRerankerClient, product_vector


def _pipeline(vectors, rerank_k=24):
    return RetrievalPipeline(
        query_processor=QueryProcessor(FakeLLM(enabled=False)),
        embedder=FakeEmbedder(),
        retriever=Retriever(VectorRepository(FakePineconeClient(vectors)), dense_k=40),
        reranker=Reranker(FakeRerankerClient()),
        rerank_candidates_k=rerank_k,
        outfit_dense_k=10,
    )


CATALOG = [
    product_vector("WD1", "Women's wedding guest dress", gender="women", category="dress"),
    product_vector("WT1", "Women's silk wedding blouse", gender="women", category="blouse"),
    product_vector("WB1", "Women's pleated wedding skirt", gender="women", category="skirt"),
    product_vector("WF1", "Women's wedding heels shoes", gender="women", category="shoes"),
    product_vector("MT1", "Men's wedding dress shirt", gender="men", category="shirt"),
    product_vector("MB1", "Men's wedding suit trousers", gender="men", category="trousers"),
    product_vector("MF1", "Men's leather wedding shoes", gender="men", category="shoes"),
    product_vector("MD1", "Mens Dress Tuxedo Vest", gender="men", category="dress"),  # mis-tagged at ingestion
    product_vector("K1", "Kids flower girl dress for wedding", gender="kids", category="dress"),
]

GROUP_OF = {"blouse": "tops", "shirt": "tops", "skirt": "bottoms", "trousers": "bottoms", "shoes": "footwear"}


def _categories(outcome):
    return {m.product.category for m in outcome.matches}


def test_outfit_query_returns_tops_bottoms_and_footwear_for_both_genders():
    outcome = _pipeline(CATALOG).run("outfit for a wedding", top_k=12)
    ids = {m.product.product_id for m in outcome.matches}

    assert ids == {"WT1", "WB1", "WF1", "MT1", "MB1", "MF1"}  # no dresses, no kids
    assert outcome.applied_filters == {"outfit": "tops, bottoms, footwear"}


def test_outfit_groups_are_interleaved_not_bunched():
    outcome = _pipeline(CATALOG).run("wedding attire", top_k=12)
    first_three = [GROUP_OF[m.product.category] for m in outcome.matches[:3]]
    assert sorted(first_three) == ["bottoms", "footwear", "tops"]


def test_outfit_query_for_one_gender_stays_single_gender():
    outcome = _pipeline(CATALOG).run("outfit for my husband for a wedding", top_k=12)
    assert {m.product.gender for m in outcome.matches} == {"men"}
    assert _categories(outcome) == {"shirt", "trousers", "shoes"}


def test_dress_query_returns_only_dresses_and_skips_the_mens_pool():
    outcome = _pipeline(CATALOG).run("I need a dress for wedding", top_k=12)
    assert [m.product.product_id for m in outcome.matches] == ["WD1"]  # not the men's vest, not kids
    assert outcome.applied_filters == {"category": "dress"}


def test_specific_garment_query_is_not_an_outfit_query():
    outcome = _pipeline(CATALOG).run("women skirt for wedding", top_k=12)
    assert _categories(outcome) == {"skirt"}
    assert outcome.applied_filters == {"gender": "women", "category": "skirt"}


def test_top_k_is_capped_by_rerank_budget():
    vectors = [product_vector(f"S{i}", f"Shirt {i}", gender="men", category="shirt") for i in range(20)]
    outcome = _pipeline(vectors, rerank_k=4).run("men shirt", top_k=10)
    assert len(outcome.matches) == 4
