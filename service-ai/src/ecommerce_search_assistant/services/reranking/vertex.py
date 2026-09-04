from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any

from ecommerce_search_assistant.core.config import Settings, get_settings


@dataclass
class VertexRankingRerankService:
    """Stateless reranking through the managed Google Cloud Ranking API."""

    settings: Settings = field(default_factory=get_settings)
    _client: Any | None = field(default=None, init=False, repr=False)
    _types: Any | None = field(default=None, init=False, repr=False)
    _verified: bool = field(default=False, init=False, repr=False)

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        if len(documents) > 200:
            raise ValueError("Google Cloud Ranking API accepts at most 200 records per request")

        client, discoveryengine = self._get_components()
        ranking_config = client.ranking_config_path(
            project=self._project_id(),
            location=self.settings.reranker_location,
            ranking_config=self.settings.reranker_config_id,
        )
        request = discoveryengine.RankRequest(
            ranking_config=ranking_config,
            model=self.settings.reranker_model_name,
            top_n=len(documents),
            query=query,
            records=[
                discoveryengine.RankingRecord(id=str(index), content=document)
                for index, document in enumerate(documents)
            ],
            ignore_record_details_in_response=True,
        )
        response = client.rank(
            request=request,
            timeout=self.settings.reranker_timeout_seconds,
        )

        scores_by_id: dict[str, float] = {}
        for record in response.records:
            score = float(record.score)
            if not isfinite(score):
                raise RuntimeError("Google Cloud Ranking API returned a non-finite score")
            scores_by_id[str(record.id)] = score

        expected_ids = {str(index) for index in range(len(documents))}
        if set(scores_by_id) != expected_ids:
            raise RuntimeError("Google Cloud Ranking API returned incomplete record scores")
        self._verified = True
        return [scores_by_id[str(index)] for index in range(len(documents))]

    def warmup(self) -> None:
        # Constructing the SDK client does not validate a short-lived OAuth
        # token. Make one minimal request so readiness cannot claim reranking is
        # usable while every real search silently falls back after a 401.
        self.rerank("catalog readiness", ["catalog readiness"])

    def is_ready(self) -> bool:
        return self._verified

    def _project_id(self) -> str:
        project_id = (self.settings.google_cloud_project or "").strip()
        if not project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required when reranking is enabled")
        return project_id

    def _get_components(self) -> tuple[Any, Any]:
        if self._client is None or self._types is None:
            self._project_id()
            from google.cloud import discoveryengine_v1 as discoveryengine

            client_options: dict[str, Any] = {}
            access_token = self._load_access_token()
            if access_token:
                from google.oauth2.credentials import Credentials

                client_options["credentials"] = Credentials(token=access_token)
            self._client = discoveryengine.RankServiceClient(**client_options)
            self._types = discoveryengine
        return self._client, self._types

    def _load_access_token(self) -> str | None:
        """Read an optional short-lived token for local Docker only.

        Production leaves this unset and uses Application Default Credentials.
        """
        if not self.settings.google_cloud_reranker_access_token_file:
            return None
        path = Path(self.settings.google_cloud_reranker_access_token_file).expanduser()
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(
                f"Could not read GOOGLE_CLOUD_RERANKER_ACCESS_TOKEN_FILE: {path}"
            ) from exc
        if not value:
            raise RuntimeError(
                f"GOOGLE_CLOUD_RERANKER_ACCESS_TOKEN_FILE is empty: {path}"
            )
        return value
