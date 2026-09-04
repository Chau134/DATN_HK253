from ecommerce_search_assistant.services.reranking.mock import MockRerankService


def test_mock_rerank_is_deterministic() -> None:
    service = MockRerankService()
    first = service.rerank("red shoes", ["doc a", "doc b", "doc c"])
    second = service.rerank("red shoes", ["doc a", "doc b", "doc c"])

    assert first == second
    assert len(first) == 3
    assert all(0.0 <= score <= 1.0 for score in first)


def test_mock_rerank_empty_documents() -> None:
    assert MockRerankService().rerank("anything", []) == []


def test_mock_rerank_score_depends_on_query_and_document() -> None:
    service = MockRerankService()
    same_doc_diff_query = {
        service.rerank("q1", ["same doc"])[0],
        service.rerank("q2", ["same doc"])[0],
    }
    assert len(same_doc_diff_query) == 2
