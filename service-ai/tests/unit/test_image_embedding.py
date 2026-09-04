from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

torch = pytest.importorskip("torch", reason="local-models optional dependency is not installed")

from ecommerce_search_assistant.core.config import Settings
from ecommerce_search_assistant.services.embeddings.image import TransformersImageEmbeddingService


class FakeProcessor:
    def __call__(self, images: list[Any], return_tensors: str) -> dict[str, torch.Tensor]:
        assert images
        assert return_tensors == "pt"
        return {"pixel_values": torch.zeros((len(images), 3, 2, 2))}


class FakeSiglipModel:
    def get_image_features(self, **_: Any) -> SimpleNamespace:
        return SimpleNamespace(pooler_output=torch.tensor([[3.0, 4.0]]))


def test_image_embedding_uses_pooler_output_when_model_returns_object(
    settings: Settings,
    pil_image: Any,
) -> None:
    service = TransformersImageEmbeddingService(settings=settings)
    service._model = FakeSiglipModel()
    service._processor = FakeProcessor()
    service._torch = torch

    vectors = service.embed_batch([pil_image])

    assert vectors == [pytest.approx([0.6, 0.8])]
