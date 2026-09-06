from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from pydantic import BaseModel

from ecommerce_search_assistant.services.llm.service import BaseLlmService, QueryUnderstanding

logger = logging.getLogger(__name__)


class BedrockService(BaseLlmService):
    @property
    def is_enabled(self) -> bool:
        return bool(self.settings.bedrock_model_id)

    def warmup(self) -> None:
        client = self._get_client()
        self._runtime_ready = _has_bedrock_credentials(client)

    def is_ready(self) -> bool:
        return bool(getattr(self, "_runtime_ready", False))

    def _generate_json(self, prompt: str, schema: type[BaseModel]) -> Any:
        max_tokens = (
            self.settings.bedrock_query_understanding_max_tokens
            if schema is QueryUnderstanding
            else self.settings.bedrock_max_tokens
        )
        try:
            response = self._get_client().converse(
                modelId=self.settings.bedrock_model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": _json_prompt(prompt, schema)}],
                    }
                ],
                inferenceConfig=_inference_config(
                    self.settings,
                    temperature=0.0,
                    max_tokens=max_tokens,
                ),
            )
        except Exception:
            self._runtime_ready = False
            raise
        self._runtime_ready = True
        return schema.model_validate_json(_json_from_text(_response_text(response)))

    def _get_client(self) -> Any:
        if self._client is None:
            _normalize_bedrock_bearer_token()

            import boto3
            from botocore.config import Config

            kwargs: dict[str, Any] = {
                "region_name": self.settings.bedrock_region,
                "config": Config(
                    connect_timeout=self.settings.bedrock_timeout_seconds,
                    read_timeout=self.settings.bedrock_timeout_seconds,
                    retries={"max_attempts": self.settings.bedrock_retry_attempts},
                ),
            }
            if self.settings.bedrock_endpoint_url:
                kwargs["endpoint_url"] = self.settings.bedrock_endpoint_url
            self._client = boto3.client("bedrock-runtime", **kwargs)
        return self._client


def _normalize_bedrock_bearer_token() -> None:
    variable = "AWS_BEARER_TOKEN_BEDROCK"
    token = os.environ.get(variable)
    if token is not None:
        normalized = token.strip()
        if normalized:
            os.environ[variable] = normalized
        else:
            os.environ.pop(variable, None)


def _has_bedrock_credentials(client: Any) -> bool:
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "").strip():
        return True
    signer = getattr(client, "_request_signer", None)
    return getattr(signer, "_credentials", None) is not None


def _inference_config(
    settings: Any,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "temperature": (
            settings.bedrock_temperature
            if temperature is None
            else temperature
        ),
        "maxTokens": settings.bedrock_max_tokens if max_tokens is None else max_tokens,
    }
    if settings.bedrock_top_p is not None:
        config["topP"] = settings.bedrock_top_p
    return config


def _json_prompt(prompt: str, schema: type[BaseModel]) -> str:
    return (
        f"{prompt}\n\n"
        "Return only a single JSON document. Do not wrap it in markdown fences.\n"
        "The JSON must validate against this schema:\n"
        f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
    )


def _response_text(response: dict[str, Any]) -> str:
    content = response.get("output", {}).get("message", {}).get("content", [])
    texts = [block.get("text", "") for block in content if isinstance(block, dict) and block.get("text")]
    text = "".join(texts).strip()
    if not text:
        logger.debug("bedrock_empty_text_response response=%s", response)
        raise ValueError("Bedrock response did not contain text output")
    return text


def _json_from_text(text: str) -> str:
    stripped = text.strip()
    fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        stripped = fence_match.group(1).strip()

    try:
        json.loads(stripped)
        return stripped
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        candidate = stripped[start : end + 1]
        json.loads(candidate)
        return candidate

    raise ValueError("Bedrock response was not valid JSON")
