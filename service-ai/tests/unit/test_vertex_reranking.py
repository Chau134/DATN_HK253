from types import SimpleNamespace

import pytest

from ecommerce_search_assistant.services.reranking.vertex import VertexRankingRerankService


class _FakeDiscoveryEngine:
    @staticmethod
    def RankingRecord(**kwargs):
        return SimpleNamespace(**kwargs)

    @staticmethod
    def RankRequest(**kwargs):
        return SimpleNamespace(**kwargs)


class _FakeRankClient:
    def __init__(self, records: list[SimpleNamespace]) -> None:
        self.response_records = records
        self.request = None
        self.timeout = None

    @staticmethod
    def ranking_config_path(*, project: str, location: str, ranking_config: str) -> str:
        return f"projects/{project}/locations/{location}/rankingConfigs/{ranking_config}"

    def rank(self, *, request, timeout: float):
        self.request = request
        self.timeout = timeout
        return SimpleNamespace(records=self.response_records)


def _service(settings, response_records: list[SimpleNamespace]):
    service = VertexRankingRerankService(
        settings=settings.model_copy(update={"google_cloud_project": "test-project"})
    )
    client = _FakeRankClient(response_records)
    service._client = client
    service._types = _FakeDiscoveryEngine
    return service, client


def test_vertex_reranker_returns_scores_in_input_order(settings) -> None:
    service, client = _service(
        settings,
        [
            SimpleNamespace(id="1", score=0.91),
            SimpleNamespace(id="0", score=0.12),
        ],
    )

    scores = service.rerank("áo đen đi làm", ["document one", "document two"])

    assert scores == [0.12, 0.91]
    assert client.request.model == "semantic-ranker-default@latest"
    assert client.request.top_n == 2
    assert client.request.ignore_record_details_in_response is True
    assert client.request.ranking_config.endswith("/rankingConfigs/default_ranking_config")
    assert [record.id for record in client.request.records] == ["0", "1"]
    assert client.timeout == 10.0
    assert service.is_ready() is True


def test_vertex_reranker_warmup_verifies_remote_credentials(settings) -> None:
    service, client = _service(settings, [SimpleNamespace(id="0", score=0.75)])

    assert service.is_ready() is False

    service.warmup()

    assert service.is_ready() is True
    assert client.request.query == "catalog readiness"


def test_vertex_reranker_rejects_incomplete_response(settings) -> None:
    service, _ = _service(settings, [SimpleNamespace(id="0", score=0.5)])

    with pytest.raises(RuntimeError, match="incomplete record scores"):
        service.rerank("query", ["document one", "document two"])


def test_vertex_reranker_skips_api_for_empty_documents(settings) -> None:
    service, client = _service(settings, [])

    assert service.rerank("query", []) == []
    assert client.request is None


def test_vertex_reranker_reads_short_lived_token_file(settings, tmp_path) -> None:
    token_file = tmp_path / "reranker-access-token"
    token_file.write_text("temporary-access-token\n", encoding="utf-8")
    service = VertexRankingRerankService(
        settings=settings.model_copy(
            update={
                "google_cloud_project": "test-project",
                "google_cloud_reranker_access_token_file": str(token_file),
            }
        )
    )

    assert service._load_access_token() == "temporary-access-token"
