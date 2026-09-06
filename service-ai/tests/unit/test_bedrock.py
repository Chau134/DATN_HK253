import os
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

from ecommerce_search_assistant.core.config import Settings, get_settings
from ecommerce_search_assistant.services.bedrock.service import (
    BedrockService,
    _inference_config,
    _normalize_bedrock_bearer_token,
)
from ecommerce_search_assistant.services.llm.factory import get_llm_service
from ecommerce_search_assistant.services.llm.service import QueryUnderstanding


class _Payload(BaseModel):
    value: str


class _FakeBedrockClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._request_signer = SimpleNamespace(_credentials=object())

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"output": {"message": {"content": [{"text": '{"value": "ok"}'}]}}}


class _FailingBedrockClient(_FakeBedrockClient):
    def converse(self, **kwargs: Any) -> dict[str, Any]:
        del kwargs
        raise RuntimeError("bedrock unavailable")


def test_bedrock_defaults_target_gpt_oss_120b_in_tokyo() -> None:
    settings = Settings(_env_file=None)

    assert settings.bedrock_region == "ap-northeast-1"
    assert settings.bedrock_model_id == "openai.gpt-oss-120b-1:0"


def test_bedrock_generate_json_uses_converse(settings: Settings) -> None:
    service = BedrockService(settings=settings)
    fake_client = _FakeBedrockClient()
    service._client = fake_client

    payload = service._generate_json("Return a value.", _Payload)

    assert payload.value == "ok"
    assert fake_client.calls[0]["modelId"] == settings.bedrock_model_id
    assert fake_client.calls[0]["inferenceConfig"]["temperature"] == 0.0


def test_bedrock_reply_generation_can_be_made_deterministic(
    settings: Settings,
) -> None:
    config = _inference_config(settings, temperature=0.0)

    assert config["temperature"] == 0.0
    assert config["maxTokens"] == settings.bedrock_max_tokens


def test_bedrock_query_understanding_uses_smaller_output_budget(
    settings: Settings,
) -> None:
    service = BedrockService(settings=settings)
    fake_client = _FakeBedrockClient()
    fake_client.converse = lambda **kwargs: (
        fake_client.calls.append(kwargs)
        or {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": (
                                '{"intent":"search_product","rewritten_query":"áo",'
                                '"filters":{},"needs_image_search":false,'
                                '"needs_text_search":true,"clarifying_question":null,'
                                '"referenced_product_ids":[]}'
                            )
                        }
                    ]
                }
            }
        }
    )
    service._client = fake_client

    service._generate_json("Analyze.", QueryUnderstanding)

    assert (
        fake_client.calls[0]["inferenceConfig"]["maxTokens"]
        == settings.bedrock_query_understanding_max_tokens
    )


def test_bedrock_readiness_tracks_credentials_and_successful_call(
    settings: Settings,
    monkeypatch,
) -> None:
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
    service = BedrockService(settings=settings)

    assert service.is_ready() is False

    service._client = _FakeBedrockClient()
    service.warmup()

    assert service.is_ready() is True

    service._runtime_ready = False
    service._generate_json("Return a value.", _Payload)

    assert service.is_ready() is True


def test_bedrock_readiness_is_false_without_credentials_or_after_call_failure(
    settings: Settings,
    monkeypatch,
) -> None:
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
    service = BedrockService(settings=settings)
    service._client = SimpleNamespace(
        _request_signer=SimpleNamespace(_credentials=None),
    )

    service.warmup()

    assert service.is_ready() is False

    service._client = _FailingBedrockClient()
    service._runtime_ready = True

    try:
        service._generate_json("Return a value.", _Payload)
    except RuntimeError:
        pass

    assert service.is_ready() is False


def test_bedrock_bearer_token_is_trimmed(monkeypatch) -> None:
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "ABSK-example\r\n")

    _normalize_bedrock_bearer_token()

    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "ABSK-example"


def test_empty_bedrock_bearer_token_is_removed(monkeypatch) -> None:
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "  \r\n")

    _normalize_bedrock_bearer_token()

    assert "AWS_BEARER_TOKEN_BEDROCK" not in os.environ


def test_llm_factory_selects_bedrock(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    get_settings.cache_clear()
    get_llm_service.cache_clear()

    service = get_llm_service()

    assert isinstance(service, BedrockService)
    get_llm_service.cache_clear()
    get_settings.cache_clear()
