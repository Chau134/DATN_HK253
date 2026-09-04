import pytest
from PIL import Image

from ecommerce_search_assistant.core.config import Settings
from ecommerce_search_assistant.services.cropping.yolo import (
    OriginalImageCropService,
    YoloCropService,
)


def test_original_image_crop_service_never_loads_yolo() -> None:
    service = OriginalImageCropService()
    source = Image.new("RGBA", (16, 12), color=(1, 2, 3, 4))

    service.warmup()
    crops = service.detect_and_crop(source)

    assert service.is_ready() is True
    assert len(crops) == 1
    assert crops[0].is_fallback is True
    assert crops[0].bbox == (0, 0, 16, 12)
    assert crops[0].image.mode == "RGB"


def test_yolo_no_detection_falls_back_to_original_image(
    settings: Settings,
    monkeypatch,
) -> None:
    service = YoloCropService(settings=settings)
    source = Image.new("RGB", (16, 12), color=(1, 2, 3))
    monkeypatch.setattr(service, "_detect", lambda image: [])

    crops = service.detect_and_crop(source)

    assert len(crops) == 1
    assert crops[0].is_fallback is True
    assert crops[0].bbox == (0, 0, 16, 12)
    assert crops[0].image.size == source.size


def test_yolo_filters_tiny_boxes_and_prefers_confident_reasonable_crop(
    settings: Settings,
    monkeypatch,
) -> None:
    settings = settings.model_copy(update={"yolo_min_crop_side_px": 6})
    service = YoloCropService(settings=settings)
    source = Image.new("RGB", (100, 100), color=(1, 2, 3))
    monkeypatch.setattr(
        service,
        "_detect",
        lambda image: [
            ((10, 10, 14, 14), 0.99, 1),
            ((0, 0, 90, 90), 0.70, 1),
            ((20, 20, 60, 60), 0.80, 1),
        ],
    )

    crops = service.detect_and_crop(source)

    assert crops[0].bbox == (20, 20, 60, 60)
    assert all(crop.bbox != (10, 10, 14, 14) for crop in crops)


def test_yolo_missing_weights_fails_fast_and_caches_error(settings: Settings, tmp_path) -> None:
    settings = settings.model_copy(update={"yolo_weights_path": str(tmp_path / "missing.pt")})
    service = YoloCropService(settings=settings)

    with pytest.raises(RuntimeError, match="YOLO weights file does not exist") as first:
        service.warmup()
    with pytest.raises(RuntimeError, match="YOLO weights file does not exist") as second:
        service.warmup()

    assert first.value is second.value
