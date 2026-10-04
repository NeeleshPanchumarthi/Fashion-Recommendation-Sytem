from app.repositories.vector_repository import VectorRepository
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.query_processor import QueryProcessor
from app.retrieval.reranker import Reranker
from app.retrieval.retriever import Retriever
from tests.fakes import FakeEmbedder, FakeLLM, FakePineconeClient, FakeRerankerClient, product_vector


def _pipeline(vectors, llm=None, rerank_k=30):
    return RetrievalPipeline(
        query_processor=QueryProcessor(llm or FakeLLM(enabled=False)),
        embedder=FakeEmbedder(),
        retriever=Retriever(VectorRepository(FakePineconeClient(vectors)), dense_k=50),
        reranker=Reranker(FakeRerankerClient()),
        rerank_candidates_k=rerank_k,
    )


CATALOG = [
    product_vector("W1", "Women's wedding guest dress", gender="women", category="dress"),
    product_vector("W2", "Women's floral dress", gender="women", category="dress"),
    product_vector("M1", "Men's wedding dress shirt", gender="men", category="shirt"),
    product_vector("M2", "Men's tuxedo vest", gender="men", category="not distributed"),
    product_vector("K1", "Kids flower girl dress for wedding", gender="kids", category="dress"),
]


def test_genderless_query_mixes_men_and_women_and_skips_kids():
    outcome = _pipeline(CATALOG).run("dress for wedding", top_k=10)
    ids = [m.product.product_id for m in outcome.matches]

    assert set(ids) == {"W1", "W2", "M1", "M2"}
    assert {ids[0][0], ids[1][0]} == {"W", "M"}  # alternates between pools
    assert outcome.applied_filters == {"category": "dress"}


def test_gendered_query_stays_single_gender():
    outcome = _pipeline(CATALOG).run("women dress for wedding", top_k=10)
    assert [m.product.product_id for m in outcome.matches][0] == "W1"
    assert {m.product.gender for m in outcome.matches} == {"women"}


def test_top_k_is_capped_by_rerank_budget():
    vectors = [product_vector(f"S{i}", f"Shirt {i}", gender="men", category="shirt") for i in range(20)]
    outcome = _pipeline(vectors, rerank_k=4).run("men shirt", top_k=10)
    assert len(outcome.matches) == 4
